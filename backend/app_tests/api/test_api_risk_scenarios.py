import pytest
from rest_framework.test import APIClient
from core.models import (
    Asset,
    Perimeter,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    AppliedControl,
    Threat,
)
from iam.models import Folder

from test_utils import EndpointTestsQueries, EndpointTestsUtils
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

# Generic perimeter data for tests
RISK_SCENARIO_NAME = "Test scenario"
RISK_SCENARIO_DESCRIPTION = "Test Description"
RISK_SCENARIO_REF_ID = "Ref ID"
RISK_SCENARIO_CURRENT_PROBABILITIES = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "Frequent event",
    "hexcolor": "#FF0000",
    "annotation": None,
    "translations": {
        "de": {"name": "Hoch", "description": "Häufiges Ereignis"},
    },
}

RISK_SCENARIO_CURRENT_PROBABILITIES2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Occasional event",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {"name": "Mittel", "description": "Gelegentliches Ereignis"},
    },
}

RISK_SCENARIO_CURRENT_IMPACT = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "High impact",
    "hexcolor": "#FF0000",
    "annotation": None,
    "translations": {
        "de": {"name": "Hoch", "description": "Hohe Auswirkung"},
    },
}

RISK_SCENARIO_CURRENT_IMPACT2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Medium impact",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {"name": "Mittel", "description": "Mittlere Auswirkung"},
    },
}

RISK_SCENARIO_CURRENT_LEVEL = {
    "value": 2,
    "abbreviation": "H",
    "name": "High",
    "description": "unacceptable risk",
    "hexcolor": "#FF0000",
    "annotation": None,
    "translations": {
        "de": {"name": "Hoch", "description": "Inakzeptables Risiko"},
    },
}
RISK_SCENARIO_CURRENT_LEVEL2 = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "risk requiring mitigation within 2 years",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {
            "name": "Mittel",
            "description": "Risiko mit Behandlungsbedarf innerhalb von 2 Jahren",
        },
    },
}

RISK_SCENARIO_RESIDUAL_PROBABILITIES = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Occasional event",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {"name": "Mittel", "description": "Gelegentliches Ereignis"},
    },
}
RISK_SCENARIO_RESIDUAL_PROBABILITIES2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "Unfrequent event",
    "hexcolor": "#92D050",
    "annotation": None,
    "translations": {
        "de": {"name": "Gering", "description": "Seltenes Ereignis"},
    },
}

RISK_SCENARIO_RESIDUAL_IMPACT = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "Medium impact",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {"name": "Mittel", "description": "Mittlere Auswirkung"},
    },
}

RISK_SCENARIO_RESIDUAL_IMPACT2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "Low impact",
    "hexcolor": "#92D050",
    "annotation": None,
    "translations": {
        "de": {"name": "Gering", "description": "Geringe Auswirkung"},
    },
}

RISK_SCENARIO_RESIDUAL_LEVEL = {
    "value": 1,
    "abbreviation": "M",
    "name": "Medium",
    "description": "risk requiring mitigation within 2 years",
    "hexcolor": "#FFFF00",
    "annotation": None,
    "translations": {
        "de": {
            "name": "Mittel",
            "description": "Risiko mit Behandlungsbedarf innerhalb von 2 Jahren",
        },
    },
}
RISK_SCENARIO_RESIDUAL_LEVEL2 = {
    "value": 0,
    "abbreviation": "L",
    "name": "Low",
    "description": "acceptable risk",
    "hexcolor": "#00FF00",
    "annotation": None,
    "translations": {
        "de": {"name": "Gering", "description": "Akzeptables Risiko"},
    },
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
                    perimeter=Perimeter.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(
                        name="test",
                        folder=folder,
                        json_definition=RISK_MATRIX_JSON_DEFINITION,
                    ),
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
                    perimeter=Perimeter.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(
                        name="test",
                        folder=folder,
                        json_definition=RISK_MATRIX_JSON_DEFINITION,
                    ),
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
                    perimeter=Perimeter.objects.create(name="test", folder=folder),
                    risk_matrix=RiskMatrix.objects.create(
                        name="test",
                        folder=folder,
                        json_definition=RISK_MATRIX_JSON_DEFINITION,
                    ),
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
            perimeter=Perimeter.objects.create(
                name="testPerimeter", folder=test.folder
            ),
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
                    "is_locked": False,
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
            perimeter=Perimeter.objects.create(name="test", folder=test.folder),
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
                    "is_locked": False,
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
            perimeter=Perimeter.objects.create(name="test", folder=test.folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        threat = Threat.objects.create(name="test", folder=test.folder)
        threat2 = Threat.objects.create(name="test2", folder=test.folder)
        asset = Asset.objects.create(name="test", folder=test.folder)
        applied_controls = AppliedControl.objects.create(
            name="test", folder=test.folder
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Risk Scenarios",
            RiskScenario,
            {
                "name": RISK_SCENARIO_NAME,
                "description": RISK_SCENARIO_DESCRIPTION,
                "ref_id": RISK_SCENARIO_REF_ID,
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
                "current_proba": RISK_SCENARIO_CURRENT_PROBABILITIES2["value"],
                "current_impact": RISK_SCENARIO_CURRENT_IMPACT2["value"],
                "current_level": RISK_SCENARIO_CURRENT_LEVEL2["value"],
                "residual_proba": RISK_SCENARIO_RESIDUAL_PROBABILITIES2["value"],
                "residual_impact": RISK_SCENARIO_RESIDUAL_IMPACT2["value"],
                "residual_level": RISK_SCENARIO_RESIDUAL_LEVEL2["value"],
                "treatment": RISK_SCENARIO_TREATMENT_STATUS2[0],
                "justification": "new " + RISK_SCENARIO_JUSTIFICATION,
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
                    "is_locked": False,
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
            perimeter=Perimeter.objects.create(name="testPerimeter", folder=folder),
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


@pytest.mark.django_db
class TestRiskScenarioLevelFilter:
    """Regression tests for multi-value current_level / residual_level filtering.

    Selecting several levels in the UI sends repeated query params
    (?current_level=1&current_level=2); the backend must match *all* of them, not
    just the last one. See IntegerInFilter in core/views.py.
    """

    def _build_scenarios(self, authenticated_client):
        """Create one risk assessment with four scenarios at known levels.

        Returns a dict mapping (current_level, residual_level) -> ref_id.
        Levels are forced via .update() to bypass save()-time matrix scoring.
        """
        EndpointTestsQueries.Auth.import_object(authenticated_client, "Risk matrix")
        folder = Folder.objects.create(
            name="filter-test", content_type=Folder.ContentType.DOMAIN
        )
        risk_assessment = RiskAssessment.objects.create(
            name="ra",
            perimeter=Perimeter.objects.create(name="p", folder=folder),
            risk_matrix=RiskMatrix.objects.all()[0],
        )
        # (current_level, residual_level) pairs; -1 represents the "--" (unrated) level.
        # Values stay within the 3-level test matrix (indices 0..2) so serialization
        # of the matched scenarios does not index out of range.
        levels = [(-1, -1), (0, 0), (1, 1), (2, 2)]
        ref_by_levels = {}
        for index, (current, residual) in enumerate(levels):
            ref_id = f"R{index}"
            scenario = RiskScenario.objects.create(
                name=f"scenario-{index}",
                ref_id=ref_id,
                risk_assessment=risk_assessment,
            )
            RiskScenario.objects.filter(id=scenario.id).update(
                current_level=current, residual_level=residual
            )
            ref_by_levels[(current, residual)] = ref_id
        return ref_by_levels

    @staticmethod
    def _get(authenticated_client, params):
        url = EndpointTestsUtils.get_endpoint_url("Risk Scenarios")
        return authenticated_client.get(url, params)

    def test_current_level_keeps_all_repeated_values(self, authenticated_client):
        """?current_level=1&current_level=2 must return both levels, not only the last."""
        ref_by_levels = self._build_scenarios(authenticated_client)

        response = self._get(authenticated_client, {"current_level": [1, 2]})

        assert response.status_code == 200
        returned = {row["ref_id"] for row in response.json()["results"]}
        expected = {
            ref
            for (current, _residual), ref in ref_by_levels.items()
            if current in {1, 2}
        }
        assert returned == expected

    def test_residual_level_accepts_negative_and_positive(self, authenticated_client):
        """?residual_level=-1&residual_level=2 must match the '--' and '2' levels."""
        ref_by_levels = self._build_scenarios(authenticated_client)

        response = self._get(authenticated_client, {"residual_level": [-1, 2]})

        assert response.status_code == 200
        returned = {row["ref_id"] for row in response.json()["results"]}
        expected = {
            ref
            for (_current, residual), ref in ref_by_levels.items()
            if residual in {-1, 2}
        }
        assert returned == expected

    def test_single_value_still_works(self, authenticated_client):
        """A single value must behave like an exact match (no regression)."""
        ref_by_levels = self._build_scenarios(authenticated_client)

        response = self._get(authenticated_client, {"current_level": [2]})

        assert response.status_code == 200
        returned = {row["ref_id"] for row in response.json()["results"]}
        expected = {
            ref for (current, _residual), ref in ref_by_levels.items() if current == 2
        }
        assert returned == expected

    def test_non_integer_value_is_rejected(self, authenticated_client):
        """Non-integer input must be rejected with 400, not silently coerced."""
        self._build_scenarios(authenticated_client)

        response = self._get(authenticated_client, {"current_level": "abc"})

        assert response.status_code == 400

    def test_decimal_value_is_rejected(self, authenticated_client):
        """1.9 must not be truncated to 1; it must be rejected with 400."""
        self._build_scenarios(authenticated_client)

        response = self._get(authenticated_client, {"current_level": "1.9"})

        assert response.status_code == 400
