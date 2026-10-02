import copy

import pytest

from core.models import RiskMatrix, Terminology
from core.views import RiskMatrixViewSet
from ebios_rm import rating_kit
from ebios_rm.models import KillChain, RoTo
from ebios_rm.serializers import RoToReadSerializer
from ebios_rm.tests.test_kill_chain_steps import (
    _operating_mode,
    admin_client,
    elementary_actions_fixture,
)

from ebios_rm.tests.fixtures import *

LEGACY_PERTINENCE_MATRIX = [
    [1, 1, 2, 2],
    [1, 2, 3, 3],
    [2, 3, 3, 4],
    [2, 3, 4, 4],
]

CUSTOM_SECTION = {
    "success_probability": [{"name": f"Pr{i}"} for i in range(1, 5)],
    "technical_difficulty": [{"name": f"D{i}"} for i in range(1, 5)],
    "likelihood_grid": [[0] * 4, [0] * 4, [0] * 4, [3, 3, 3, 3]],
    "ro_to": {
        "motivation": [{"name": f"M{i}"} for i in range(1, 5)],
        "pertinence": [{"name": f"P{i}"} for i in range(1, 5)],
        "pertinence_grid": [[3] * 4] * 4,
    },
}


def _custom_matrix(base: RiskMatrix, section=CUSTOM_SECTION) -> RiskMatrix:
    definition = copy.deepcopy(base.json_definition)
    definition["ebios_rm"] = copy.deepcopy(section)
    return RiskMatrix.objects.create(
        name="EBIOS RM corporate matrix",
        urn="urn:test:risk:matrix:ebios-rm-corporate",
        folder=base.folder,
        json_definition=definition,
    )


def _ro_to(study, motivation=0, resources=0):
    objective = f"objective {motivation}-{resources}"
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    return RoTo.objects.create(
        ebios_rm_study=study,
        risk_origin=risk_origin,
        target_objective=objective,
        motivation=motivation,
        resources=resources,
    )


class TestDefaults:
    def test_defaults_follow_the_probability_scale(self):
        section = rating_kit.resolve({"probability": [{}] * 4})
        assert [level["name"] for level in section["technical_difficulty"]] == [
            "difficultyNegligible",
            "difficultyLow",
            "difficultyHigh",
            "difficultyVeryHigh",
        ]
        assert len(section["success_probability"]) == 4
        assert len(section["likelihood_grid"]) == 4

    @pytest.mark.parametrize("motivation", [1, 2, 3, 4])
    @pytest.mark.parametrize("resources", [1, 2, 3, 4])
    def test_default_pertinence_matches_the_legacy_metric(self, motivation, resources):
        scales = rating_kit.resolve({"probability": [{}] * 4})["ro_to"]
        assert (
            rating_kit.pertinence(scales, motivation, resources)
            == LEGACY_PERTINENCE_MATRIX[motivation - 1][resources - 1]
        )

    def test_undefined_criteria_give_undefined_pertinence(self):
        scales = rating_kit.resolve({"probability": [{}] * 4})["ro_to"]
        assert rating_kit.pertinence(scales, 0, 3) == 0
        assert rating_kit.pertinence(scales, 3, 0) == 0

    def test_only_default_levels_are_flagged(self):
        section = rating_kit.resolve(
            {"probability": [{}] * 4, "ebios_rm": CUSTOM_SECTION}
        )
        assert section["success_probability"][0] == {"name": "Pr1"}
        assert section["ro_to"]["resources"][0] == {"name": "limited", "default": True}

    def test_partial_section_keeps_the_other_defaults(self):
        section = rating_kit.resolve(
            {"probability": [{}] * 4, "ebios_rm": {"ro_to": {"motivation": []}}}
        )
        assert section["ro_to"]["motivation"][0]["name"] == "very_low"
        assert section["ro_to"]["pertinence_grid"] == rating_kit.DEFAULT_PERTINENCE_GRID


class TestValidation:
    def test_valid_section(self):
        assert rating_kit.validate(CUSTOM_SECTION, 4) == []

    def test_missing_section_is_valid(self):
        assert rating_kit.validate(None, 4) == []

    @pytest.mark.parametrize(
        "section, fragment",
        [
            ({"success_probability": [{"name": "a"}]}, "success_probability"),
            ({"technical_difficulty": [{"name": ""}] * 4}, "missing a name"),
            ({"likelihood_grid": [[0] * 4] * 3}, "likelihood_grid"),
            ({"likelihood_grid": [[4] * 4] * 4}, "between 0 and 3"),
            ({"ro_to": {"pertinence": [{"name": "a"}] * 5}}, "ro_to.pertinence"),
            ({"ro_to": {"pertinence_grid": [[0, 1, 2, "x"]] * 4}}, "integer"),
            ("nope", "must be an object"),
        ],
    )
    def test_invalid_sections(self, section, fragment):
        errors = rating_kit.validate(section, 4)
        assert errors and any(fragment in error for error in errors), errors

    @pytest.mark.django_db
    def test_matrix_validation_includes_the_section(self, ebios_rm_matrix_fixture):
        definition = copy.deepcopy(ebios_rm_matrix_fixture.json_definition)
        assert RiskMatrixViewSet._validate_json_definition(definition) == []
        definition["ebios_rm"] = {"likelihood_grid": [[9] * 4] * 4}
        assert RiskMatrixViewSet._validate_json_definition(definition)


@pytest.mark.django_db
class TestStudyUsesItsMatrix:
    def test_custom_crossing_grid_drives_the_advanced_method(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.risk_matrix = _custom_matrix(study.risk_matrix)
        study.quotation_method = "advanced"
        study.save()
        operating_mode = _operating_mode(study)
        KillChain.objects.create(
            operating_mode=operating_mode,
            elementary_action=elementary_actions_fixture[0],
            success_probability=3,
            technical_difficulty=3,
        )
        operating_mode.refresh_likelihood()
        operating_mode.refresh_from_db()

        # default grid gives [3][3] == 1; the matrix says 3
        assert operating_mode.effective_likelihood == 3

    def test_pertinence_and_labels_follow_the_matrix(
        self, basic_ebios_rm_study_fixture
    ):
        study = basic_ebios_rm_study_fixture
        ro_to = _ro_to(study, motivation=1, resources=1)
        assert ro_to.pertinence == 1
        assert ro_to.get_motivation_display() == "very_low"

        study.risk_matrix = _custom_matrix(study.risk_matrix)
        study.save()
        ro_to = RoTo.objects.get(id=ro_to.id)

        assert ro_to.pertinence == 4
        data = RoToReadSerializer(ro_to).data
        assert data["motivation"] == "M1"
        assert data["pertinence"] == "P4"
        assert data["resources"] == "limited"

    def test_pertinence_is_sortable_and_filterable(self, basic_ebios_rm_study_fixture):
        study = basic_ebios_rm_study_fixture
        low = _ro_to(study, motivation=1, resources=1)
        high = _ro_to(study, motivation=4, resources=4)
        ordered = list(
            RoTo.objects.filter(ebios_rm_study=study).order_by("-pertinence")
        )
        assert ordered == [high, low]
        assert list(RoTo.objects.filter(pertinence=4)) == [high]


@pytest.mark.django_db
class TestRatingKitApi:
    def test_study_exposes_its_scales(self, admin_client, basic_ebios_rm_study_fixture):
        study = basic_ebios_rm_study_fixture
        study.risk_matrix = _custom_matrix(study.risk_matrix)
        study.save()

        response = admin_client.get(f"/api/ebios-rm/studies/{study.id}/rating-kit/")
        assert response.status_code == 200, response.content
        assert response.json()["technical_difficulty"][0]["name"] == "D1"
        assert response.json()["customized"] is True
        assert len(response.json()["likelihood"]) == 4

        response = admin_client.get(f"/api/ebios-rm/studies/{study.id}/motivation/")
        assert response.json() == {
            "0": "undefined",
            "1": "M1",
            "2": "M2",
            "3": "M3",
            "4": "M4",
        }

    def test_couple_choices_follow_its_study(
        self, admin_client, basic_ebios_rm_study_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.risk_matrix = _custom_matrix(study.risk_matrix)
        study.save()
        ro_to = _ro_to(study)

        response = admin_client.get(f"/api/ebios-rm/ro-to/{ro_to.id}/motivation/")
        assert response.status_code == 200, response.content
        assert response.json()["1"] == "M1"
        response = admin_client.get("/api/ebios-rm/ro-to/motivation/")
        assert response.json()["1"] == "very_low"

    def test_pertinence_is_read_only(self, admin_client, basic_ebios_rm_study_fixture):
        ro_to = _ro_to(basic_ebios_rm_study_fixture, motivation=1, resources=1)
        response = admin_client.patch(
            f"/api/ebios-rm/ro-to/{ro_to.id}/",
            {"pertinence": 4, "resources": 4},
            format="json",
        )
        assert response.status_code == 200, response.content
        ro_to.refresh_from_db()
        assert ro_to.pertinence == 2


@pytest.mark.django_db
def test_library_import_keeps_the_section(ebios_rm_matrix_fixture):
    from library.utils import RiskMatrixImporter

    data = {
        **ebios_rm_matrix_fixture.json_definition,
        "ebios_rm": CUSTOM_SECTION,
    }
    kept = {
        key: value
        for key, value in data.items()
        if key in RiskMatrixImporter.MATRIX_FIELDS
    }
    assert kept["ebios_rm"] == CUSTOM_SECTION


@pytest.mark.django_db
def test_defaults_endpoint(admin_client):
    response = admin_client.get("/api/ebios-rm/studies/rating-kit-defaults/?size=5")
    assert response.status_code == 200, response.content
    assert response.json()["likelihood_grid"][4] == [4, 4, 3, 2, 1]
    assert (
        admin_client.get(
            "/api/ebios-rm/studies/rating-kit-defaults/?size=x"
        ).status_code
        == 400
    )
