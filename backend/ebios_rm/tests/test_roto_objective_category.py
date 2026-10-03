import pytest

from core.models import Terminology
from ebios_rm.models import RoTo
from ebios_rm.serializers import RoToImportExportSerializer, RoToReadSerializer


FICHE_4_CATEGORIES = {
    "espionage",
    "strategic_prepositioning",
    "influence",
    "operational_disruption",
    "lucrative",
    "challenge_and_amusement",
}


def _couple(study, category=None, objective="steal data"):
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    return RoTo.objects.create(
        ebios_rm_study=study,
        risk_origin=risk_origin,
        target_objective=objective,
        target_objective_category=category,
    )


@pytest.mark.django_db
class TestTargetObjectiveCategory:
    def test_defaults_follow_fiche_4(self):
        Terminology.create_default_roto_target_objective_categories()
        names = set(
            Terminology.objects.filter(
                field_path=Terminology.FieldPath.ROTO_TARGET_OBJECTIVE_CATEGORY,
                builtin=True,
            ).values_list("name", flat=True)
        )
        assert names == FICHE_4_CATEGORIES

    def test_category_is_optional_and_exposed(self, basic_ebios_rm_study_fixture):
        Terminology.create_default_roto_target_objective_categories()
        espionage = Terminology.objects.get(
            name="espionage",
            field_path=Terminology.FieldPath.ROTO_TARGET_OBJECTIVE_CATEGORY,
        )
        without = _couple(basic_ebios_rm_study_fixture, objective="without")
        with_category = _couple(basic_ebios_rm_study_fixture, espionage, "with")

        assert RoToReadSerializer(without).data["target_objective_category"] is None
        assert RoToReadSerializer(with_category).data["target_objective_category"] == {
            "id": str(espionage.id),
            "str": "Espionage",
        }
        assert (
            RoToImportExportSerializer(with_category).data["target_objective_category"]
            == "espionage"
        )

    def test_filter_by_category(self, admin_client, basic_ebios_rm_study_fixture):
        Terminology.create_default_roto_target_objective_categories()
        lucrative = Terminology.objects.get(
            name="lucrative",
            field_path=Terminology.FieldPath.ROTO_TARGET_OBJECTIVE_CATEGORY,
        )
        couple = _couple(basic_ebios_rm_study_fixture, lucrative, "ransom")
        _couple(basic_ebios_rm_study_fixture, objective="other")

        response = admin_client.get(
            f"/api/ebios-rm/ro-to/?target_objective_category={lucrative.id}"
        )
        assert response.status_code == 200, response.content
        assert [row["id"] for row in response.json()["results"]] == [str(couple.id)]
