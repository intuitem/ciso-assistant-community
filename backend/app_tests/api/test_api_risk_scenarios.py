import pytest
from rest_framework.test import APIClient
from core.models import (
    Asset,
    Project,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    AppliedControl,
    Threat,
)
from iam.models import Folder

from test_utils import EndpointTestsQueries

# Generic project data for tests
RISK_SCENARIO_NAME = "Test scenario"
RISK_SCENARIO_DESCRIPTION = "Test Description"
RISK_SCENARIO_existing_controls = "Test Existing Controls"
RISK_SCENARIO_existing_controls2 = "Test New Existing Controls"
RISK_SCENARIO_REF_ID = "Ref ID"
RISK_SCENARIO_CURRENT_PROBABILITIES = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "Frequent event",
    "hexcolor": "#FF0000",
}

RISK_SCENARIO_CURRENT_PROBABILITIES2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Occasional event",
    "hexcolor": "#FFFF00",
}

RISK_SCENARIO_CURRENT_IMPACT = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "High impact",
    "hexcolor": "#FF0000",
}

RISK_SCENARIO_CURRENT_IMPACT2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Medium impact",
    "hexcolor": "#FFFF00",
}

RISK_SCENARIO_CURRENT_LEVEL = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "unacceptable risk",
    "hexcolor": "#FF0000",
}
RISK_SCENARIO_CURRENT_LEVEL2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "risk requiring mitigation within 2 years",
    "hexcolor": "#FFFF00",
}

RISK_SCENARIO_RESIDUAL_PROBABILITIES = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Occasional event",
    "hexcolor": "#FFFF00",
}
RISK_SCENARIO_RESIDUAL_PROBABILITIES2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "Unfrequent event",
    "hexcolor": "#92D050",
}

RISK_SCENARIO_RESIDUAL_IMPACT = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Medium impact",
    "hexcolor": "#FFFF00",
}

RISK_SCENARIO_RESIDUAL_IMPACT2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "Low impact",
    "hexcolor": "#92D050",
}

RISK_SCENARIO_RESIDUAL_LEVEL = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "risk requiring mitigation within 2 years",
    "hexcolor": "#FFFF00",
}
RISK_SCENARIO_RESIDUAL_LEVEL2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "acceptable risk",
    "hexcolor": "#00FF00",
}
RISK_SCENARIO_TREATMENT_STATUS = ("accept", "accept")
RISK_SCENARIO_TREATMENT_STATUS2 = ("mitigate", "mitigate")
RISK_SCENARIO_JUSTIFICATION = "Test justification"


@pytest.mark.django_db
class TestRiskScenariosUnauthenticated:
    """Perform tests on Risk Scenarios API endpoint without authentication"""

    client = APIClient()

    def test_get_risk_scenarios(self):
        """test to get risk scenarios from the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.get_object(
            self.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "risk_assessment": RiskAssessment.objects.create(
                    name="test",
                    project=Project.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(name="test", folder=folder),
                ),
            },
        )

    def test_create_risk_scenarios(self):
        """test to create risk scenarios with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
            },
        )

    def test_update_risk_scenarios(self):
        """test to update risk scenarios with the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.update_object(
            self.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "risk_assessment": RiskAssessment.objects.create(
                    name="test",
                    project=Project.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(name="test", folder=folder),
                ),
                "threats": [Threat.objects.create(name="test", folder=folder)],
            },
            {
                "name": "new " + RISK_SCENARIO_NAME,
                "description": "new " + RISK_SCENARIO_DESCRIPTION,
            },
        )

    def test_delete_risk_scenarios(self):
        """test to delete risk scenarios with the API without authentication"""

        folder = Folder.objects.create(name="test")

        EndpointTestsQueries.delete_object(
            self.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "risk_assessment": RiskAssessment.objects.create(
                    name="test",
                    project=Project.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(name="test", folder=folder),
                ),
                "threats": [Threat.objects.create(name="test", folder=folder)],
            },
        )


@pytest.mark.django_db
class TestRiskScenariosAuthenticated:
    """Perform tests on Risk Scenarios API endpoint with authentication"""

    def test_get_risk_scenarios(self, test):
        """test to get risk scenarios from the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        risk_assessment = RiskAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="testProject", folder=test.folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        threat = Threat.objects.create(name="test", folder=test.folder)

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "ref_id": RISK_SCENARIO_REF_ID,
                "existing_controls": RISK_SCENARIO_existing_controls[0],
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES["value"],
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT["value"],
                "current_level": RISK_SCENARIO_CURRENT_LEVEL["value"],
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES["value"],
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT["value"],
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL["value"],
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[0],
                "justification": RISK_SCENARIO_JUSTIFICATION,
                "risk_assessment": risk_assessment,
                "threats": [threat],
            },
            {
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES,
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT,
                "current_level": RISK_SCENARIO_CURRENT_LEVEL,
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES,
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT,
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL,
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[1],
                "risk_assessment": {
                    "id": str(risk_assessment.id),
                    "name": str(risk_assessment.name),
                    "str": str(risk_assessment),
                },
                "threats": [{"id": str(threat.id), "str": str(threat)}],
                "risk_matrix": {
                    "id": str(risk_assessment.risk_matrix.id),
                    "str": risk_assessment.risk_matrix.name,
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_risk_scenarios(self, test):
        """test to create risk scenarios with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        risk_assessment = RiskAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=test.folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        threat = Threat.objects.create(name="test", folder=test.folder)
        asset = Asset.objects.create(name="test", folder=test.folder)
        applied_controls = AppliedControl.objects.create(
            name="test", folder=test.folder
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "ref_id": RISK_SCENARIO_REF_ID,
                "existing_controls": RISK_SCENARIO_existing_controls[0],
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES["value"],
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT["value"],
                "current_level": RISK_SCENARIO_CURRENT_LEVEL["value"],
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES["value"],
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT["value"],
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL["value"],
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[0],
                "justification": RISK_SCENARIO_JUSTIFICATION,
                "risk_assessment": str(risk_assessment.id),
                "threats": [str(threat.id)],
                "assets": [str(asset.id)],
                "applied_controls": [str(applied_controls.id)],
            },
            {
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES,
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT,
                "current_level": RISK_SCENARIO_CURRENT_LEVEL,
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES,
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT,
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL,
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[1],
                "risk_assessment": {
                    "id": str(risk_assessment.id),
                    "str": str(risk_assessment),
                    "name": str(risk_assessment.name),
                },
                "threats": [{"id": str(threat.id), "str": threat.name}],
                "risk_matrix": {
                    "id": str(risk_assessment.risk_matrix.id),
                    "str": risk_assessment.risk_matrix.name,
                },
                "assets": [{"id": str(asset.id), "str": asset.name}],
                "applied_controls": [
                    {"id": str(applied_controls.id), "str": applied_controls.name}
                ],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_risk_scenarios(self, test):
        """test to update risk scenarios with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix2")
        folder = Folder.objects.create(name="test2")
        risk_assessment = RiskAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="test", folder=test.folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        risk_assessment2 = RiskAssessment.objects.create(
            name="test2",
            project=Project.objects.create(name="test2", folder=folder),
            risk_matrix=RiskMatrix.objects.all()[1],
        )
        threat = Threat.objects.create(name="test", folder=test.folder)
        threat2 = Threat.objects.create(name="test2", folder=folder)
        asset = Asset.objects.create(name="test", folder=folder)
        applied_controls = AppliedControl.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "ref_id": RISK_SCENARIO_REF_ID,
                "existing_controls": RISK_SCENARIO_existing_controls[0],
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES["value"],
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT["value"],
                "current_level": RISK_SCENARIO_CURRENT_LEVEL["value"],
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES["value"],
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT["value"],
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL["value"],
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[0],
                "justification": RISK_SCENARIO_JUSTIFICATION,
                "risk_assessment": risk_assessment,
                "threats": [threat],
            },
            {
                "name": "new " + RISK_SCENARIO_NAME,
                "description": "new " + RISK_SCENARIO_DESCRIPTION,
                "ref_id": "n" + RISK_SCENARIO_REF_ID,
                "existing_controls": RISK_SCENARIO_existing_controls2[0],
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES2["value"],
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT2["value"],
                "current_level": RISK_SCENARIO_CURRENT_LEVEL2["value"],
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES2["value"],
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT2["value"],
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL2["value"],
                "treatment": RISK_SCENARIO_TREATMENT_STATUS2[0],
                "justification": "new " + RISK_SCENARIO_JUSTIFICATION,
                "risk_assessment": str(risk_assessment2.id),
                "threats": [str(threat2.id)],
                "assets": [str(asset.id)],
                "applied_controls": [str(applied_controls.id)],
            },
            {
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES,
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT,
                "current_level": RISK_SCENARIO_CURRENT_LEVEL,
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES,
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT,
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL,
                "treatment": RISK_SCENARIO_TREATMENT_STATUS[1],
                "risk_assessment": {
                    "id": str(risk_assessment.id),
                    "str": str(risk_assessment),
                    "name": str(risk_assessment.name),
                },
                "threats": [{"id": str(threat.id), "str": threat.name}],
                "risk_matrix": {
                    "id": str(risk_assessment.risk_matrix.id),
                    "str": risk_assessment.risk_matrix.name,
                },
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_delete_risk_scenarios(self, test):
        """test to delete risk scenarios with the API with authentication"""

        EndpointTestsQueries.Auth.import_object(test.admin_client, "Risk matrix")
        folder = test.folder
        risk_assessment = RiskAssessment.objects.create(
            name="test",
            project=Project.objects.create(name="testProject", folder=folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        threat = Threat.objects.create(name="test", folder=folder)

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "risk_assessment": risk_assessment,
                "threats": [threat],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_get_treatment_choices(self, test):
        """test to get risk scenarios treatment choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Risk Scenarios",
            "treatment",
            RiskScenario.TREATMENT_OPTIONS,
            user_group=test.user_group,
        )
