"""
Risk assessment import: probability/impact labels resolve against the risk
matrix by level position, whether or not the levels carry an "id".
"""

from unittest.mock import MagicMock

import pytest

from core.models import Perimeter, RiskAssessment, RiskMatrix, RiskScenario
from data_wizard.views import (
    BaseContext,
    ConflictMode,
    RiskAssessmentRecordConsumer,
    build_matrix_mappings,
)


def _levels(*names, with_ids=False):
    return [
        {
            "abbreviation": f"L{index}",
            "name": name,
            **({"id": index} if with_ids else {}),
        }
        for index, name in enumerate(names)
    ]


# Same shape as a matrix published from the library builder: no level ids.
ID_LESS_DEFINITION = {
    "probability": _levels(
        "Très Improbable", "Improbable", "Probable", "Très probable"
    ),
    "impact": _levels("Mineur", "Important", "Majeur", "Critique"),
    "risk": _levels("Low", "Medium", "High", "Critical"),
    "grid": [[0, 0, 1, 1], [0, 1, 1, 2], [1, 1, 2, 3], [1, 2, 3, 3]],
}


@pytest.fixture
def id_less_matrix(root_folder):
    return RiskMatrix.objects.create(
        name="Builder matrix",
        folder=root_folder,
        json_definition=ID_LESS_DEFINITION,
    )


@pytest.fixture
def risk_assessment(domain_folder, id_less_matrix):
    perimeter = Perimeter.objects.create(name="Messagerie", folder=domain_folder)
    return RiskAssessment.objects.create(
        name="Messagerie",
        perimeter=perimeter,
        risk_matrix=id_less_matrix,
        folder=domain_folder,
    )


def _consumer(admin_user, risk_assessment, on_conflict=ConflictMode.UPDATE):
    request = MagicMock()
    request.user = admin_user
    return RiskAssessmentRecordConsumer(
        BaseContext(
            request=request,
            folder_id=str(risk_assessment.folder.id),
            on_conflict=on_conflict,
            target_id=str(risk_assessment.id),
        )
    )


class TestBuildMatrixMappings:
    def test_id_less_levels_map_to_their_position(self, id_less_matrix):
        mappings = build_matrix_mappings(id_less_matrix)
        assert mappings["impact"] == {
            "mineur": 0,
            "important": 1,
            "majeur": 2,
            "critique": 3,
        }
        assert mappings["probability"]["très improbable"] == 0
        assert mappings["probability"]["très probable"] == 3

    def test_translations_map_to_the_same_position(self, root_folder):
        definition = {
            **ID_LESS_DEFINITION,
            "impact": [
                {"name": "Low", "translations": {"fr": {"name": "Faible"}}},
                {"name": "High", "translations": {"fr": {"name": "Élevé"}}},
            ],
        }
        matrix = RiskMatrix.objects.create(
            name="Translated", folder=root_folder, json_definition=definition
        )
        assert build_matrix_mappings(matrix)["impact"] == {
            "low": 0,
            "faible": 0,
            "high": 1,
            "élevé": 1,
        }


class TestRiskScenarioLevels:
    def test_labels_resolve_on_an_id_less_matrix(self, admin_user, risk_assessment):
        result = _consumer(admin_user, risk_assessment).process_records(
            [
                {
                    "ref_id": "R01a",
                    "name": "Phishing",
                    "current_impact": "Critique",
                    "current_proba": " Probable",
                    "residual_impact": "important",
                    "residual_probability": "Très improbable",
                }
            ]
        )

        assert result.created == 1
        assert result.warnings == []
        scenario = RiskScenario.objects.get(ref_id="R01a")
        assert (scenario.current_impact, scenario.current_proba) == (3, 2)
        assert (scenario.residual_impact, scenario.residual_proba) == (1, 0)

    def test_unknown_label_warns_and_keeps_the_existing_rating(
        self, admin_user, risk_assessment
    ):
        RiskScenario.objects.create(
            ref_id="R01a",
            name="Phishing",
            risk_assessment=risk_assessment,
            current_impact=3,
            current_proba=2,
        )

        result = _consumer(admin_user, risk_assessment).process_records(
            [
                {
                    "ref_id": "R01a",
                    "name": "Phishing",
                    "current_impact": "Significative",
                    "current_proba": "Improbable",
                }
            ]
        )

        assert result.updated == 1
        assert len(result.warnings) == 1
        assert "current_impact 'Significative'" in result.warnings[0].error
        scenario = RiskScenario.objects.get(ref_id="R01a")
        assert scenario.current_impact == 3
        assert scenario.current_proba == 1
