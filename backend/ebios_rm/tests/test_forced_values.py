import pytest

from core.models import RiskAssessment, Terminology
from ebios_rm.helpers import build_sync_preview, sync_risk_assessment
from ebios_rm.models import (
    AttackPath,
    FearedEvent,
    OperatingMode,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from ebios_rm.serializers import (
    OperationalScenarioReadSerializer,
    OperationalScenarioWriteSerializer,
    StrategicScenarioReadSerializer,
    StrategicScenarioWriteSerializer,
)


@pytest.fixture
def scenario_chain(basic_ebios_rm_study_fixture):
    study = basic_ebios_rm_study_fixture
    severe = FearedEvent.objects.create(
        name="Data leak", ebios_rm_study=study, gravity=3, is_selected=True
    )
    minor = FearedEvent.objects.create(
        name="Defacement", ebios_rm_study=study, gravity=1, is_selected=True
    )
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    ro_to = RoTo.objects.create(
        risk_origin=risk_origin,
        target_objective="steal customer data",
        ebios_rm_study=study,
    )
    ro_to.feared_events.set([severe, minor])
    strategic_scenario = StrategicScenario.objects.create(
        name="Supplier compromise", ebios_rm_study=study, ro_to_couple=ro_to
    )
    attack_path = AttackPath.objects.create(
        name="Through the hosting provider",
        ebios_rm_study=study,
        strategic_scenario=strategic_scenario,
    )
    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study, attack_path=attack_path
    )
    return {
        "study": study,
        "minor": minor,
        "strategic_scenario": strategic_scenario,
        "attack_path": attack_path,
        "operational_scenario": operational_scenario,
    }


@pytest.mark.django_db
class TestForcedStrategicScenarioGravity:
    def test_gravity_precedence(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]
        assert strategic_scenario.gravity == 3

        strategic_scenario.focused_feared_event = scenario_chain["minor"]
        strategic_scenario.save()
        assert strategic_scenario.gravity == 1

        strategic_scenario.gravity_forced = 2
        strategic_scenario.save()
        assert strategic_scenario.gravity == 2
        assert strategic_scenario.computed_gravity == 1

        strategic_scenario.gravity_forced = None
        strategic_scenario.save()
        assert strategic_scenario.gravity == 1

    def test_forced_gravity_flows_down_to_workshop_4(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]
        strategic_scenario.gravity_forced = 0
        strategic_scenario.save()

        attack_path = AttackPath.objects.get(id=scenario_chain["attack_path"].id)
        operational_scenario = OperationalScenario.objects.get(
            id=scenario_chain["operational_scenario"].id
        )
        assert attack_path.gravity == 0
        assert operational_scenario.gravity == 0

    def test_focused_feared_event_flows_down_to_workshop_4(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]
        strategic_scenario.focused_feared_event = scenario_chain["minor"]
        strategic_scenario.save()

        assert AttackPath.objects.get(id=scenario_chain["attack_path"].id).gravity == 1

    def test_read_serializer_exposes_computed_gravity(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]
        strategic_scenario.gravity_forced = 1
        strategic_scenario.save()

        data = StrategicScenarioReadSerializer(strategic_scenario).data

        assert data["gravity_forced"] == 1
        assert data["gravity"]["value"] == 1
        assert data["computed_gravity"]["value"] == 3

    def test_forced_gravity_must_be_on_the_impact_scale(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]

        assert StrategicScenarioWriteSerializer(
            strategic_scenario, data={"gravity_forced": 3}, partial=True
        ).is_valid()
        invalid = StrategicScenarioWriteSerializer(
            strategic_scenario, data={"gravity_forced": 4}, partial=True
        )
        assert not invalid.is_valid()
        assert "gravity_forced" in invalid.errors

    def test_strategic_scenario_sync_uses_forced_gravity(self, scenario_chain):
        study = scenario_chain["study"]
        strategic_scenario = scenario_chain["strategic_scenario"]
        strategic_scenario.gravity_forced = 2
        strategic_scenario.save()
        sources = {"strategic_scenarios": [strategic_scenario]}

        preview = build_sync_preview(study, sources)
        assert preview["source_objects"][0]["impact"]["value"] == 2

        risk_assessment = RiskAssessment.objects.create(
            name="EBIOS RM sync", risk_matrix=study.risk_matrix, ebios_rm_study=study
        )
        sync_risk_assessment(risk_assessment, sources)
        risk_scenario = risk_assessment.risk_scenarios.get(name=strategic_scenario.name)
        assert 2 in (risk_scenario.inherent_impact, risk_scenario.current_impact)


@pytest.mark.django_db
class TestForcedOperationalScenarioLikelihood:
    def _operating_mode(self, operational_scenario, likelihood):
        return OperatingMode.objects.create(
            name=f"mode {likelihood}",
            operational_scenario=operational_scenario,
            likelihood=likelihood,
        )

    def test_forced_likelihood_wins_over_operating_modes(self, scenario_chain):
        study = scenario_chain["study"]
        study.quotation_method = "express"
        study.save()
        operational_scenario = scenario_chain["operational_scenario"]
        self._operating_mode(operational_scenario, 1)
        self._operating_mode(operational_scenario, 2)
        operational_scenario.refresh_from_db()
        assert operational_scenario.likelihood == 2

        operational_scenario.likelihood_forced = 0
        operational_scenario.save()
        self._operating_mode(operational_scenario, 3)
        operational_scenario.refresh_from_db()
        assert operational_scenario.likelihood == 0
        assert operational_scenario.computed_likelihood == 3

        operational_scenario.likelihood_forced = None
        operational_scenario.save()
        operational_scenario.refresh_from_db()
        assert operational_scenario.likelihood == 3

    def test_direct_estimate_has_no_computed_likelihood(self, scenario_chain):
        study = scenario_chain["study"]
        study.quotation_method = "manual"
        study.save()
        operational_scenario = scenario_chain["operational_scenario"]
        operational_scenario.likelihood = 1
        operational_scenario.save()

        data = OperationalScenarioReadSerializer(operational_scenario).data

        assert operational_scenario.computed_likelihood is None
        assert data["computed_likelihood"] is None
        assert data["likelihood"]["value"] == 1

    def test_forced_likelihood_must_be_on_the_probability_scale(self, scenario_chain):
        operational_scenario = scenario_chain["operational_scenario"]

        invalid = OperationalScenarioWriteSerializer(
            operational_scenario, data={"likelihood_forced": 4}, partial=True
        )
        assert not invalid.is_valid()
        assert "likelihood_forced" in invalid.errors

    def test_risk_level_uses_forced_values(self, scenario_chain):
        strategic_scenario = scenario_chain["strategic_scenario"]
        strategic_scenario.gravity_forced = 0
        strategic_scenario.save()
        operational_scenario = OperationalScenario.objects.get(
            id=scenario_chain["operational_scenario"].id
        )
        operational_scenario.likelihood_forced = 0
        operational_scenario.save()

        risk_level = operational_scenario.get_risk_level_display()
        matrix = operational_scenario.parsed_matrix

        assert risk_level["value"] == matrix["grid"][0][0]


@pytest.mark.django_db
def test_gravity_choices_endpoint_on_strategic_scenario(scenario_chain):
    from iam.models import User, UserGroup
    from knox.models import AuthToken
    from rest_framework.test import APIClient

    from core.apps import startup

    startup(sender=None)
    admin = User.objects.create_superuser("admin@forced-values-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )

    strategic_scenario = scenario_chain["strategic_scenario"]
    response = client.get(
        f"/api/ebios-rm/strategic-scenarios/{strategic_scenario.id}/gravity/"
    )

    assert response.status_code == 200, response.content
    impact = strategic_scenario.ebios_rm_study.parsed_matrix["impact"]
    assert len(response.json()) == len(impact) + 1
