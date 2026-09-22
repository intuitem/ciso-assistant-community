import pytest

from core.models import Terminology, Threat
from ebios_rm.models import AttackPath, OperationalScenario, RoTo, StrategicScenario
from ebios_rm.serializers import OperationalScenarioReadSerializer
from sec_intel.models import Technique

from ebios_rm.tests.fixtures import *


@pytest.fixture
def basic_attack_path_fixture(basic_ebios_rm_study_fixture):
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    ro_to = RoTo.objects.create(
        risk_origin=risk_origin,
        target_objective="test target objective",
        ebios_rm_study=basic_ebios_rm_study_fixture,
    )
    strategic_scenario = StrategicScenario.objects.create(
        name="test strategic scenario",
        ebios_rm_study=basic_ebios_rm_study_fixture,
        ro_to_couple=ro_to,
    )
    return AttackPath.objects.create(
        name="test attack path",
        ebios_rm_study=basic_ebios_rm_study_fixture,
        strategic_scenario=strategic_scenario,
    )


@pytest.fixture
def phishing_technique_fixture():
    parent = Technique.objects.create(ref_id="T1566", name="Phishing")
    return Technique.objects.create(
        ref_id="T1566.001", name="Spearphishing Attachment", parent=parent
    )


@pytest.mark.django_db
class TestOperationalScenarioTechniques:
    def test_threats_and_techniques_are_independent(
        self, basic_ebios_rm_study_fixture, basic_attack_path_fixture
    ):
        operational_scenario = OperationalScenario.objects.create(
            ebios_rm_study=basic_ebios_rm_study_fixture,
            attack_path=basic_attack_path_fixture,
        )
        threat = Threat.objects.create(name="test threat")
        technique = Technique.objects.create(ref_id="T1078", name="Valid Accounts")

        operational_scenario.threats.add(threat)
        operational_scenario.techniques.add(technique)

        assert list(operational_scenario.threats.all()) == [threat]
        assert list(operational_scenario.techniques.all()) == [technique]

        operational_scenario.threats.clear()
        assert list(operational_scenario.techniques.all()) == [technique]

    def test_read_serializer_exposes_techniques(
        self,
        basic_ebios_rm_study_fixture,
        basic_attack_path_fixture,
        phishing_technique_fixture,
    ):
        operational_scenario = OperationalScenario.objects.create(
            ebios_rm_study=basic_ebios_rm_study_fixture,
            attack_path=basic_attack_path_fixture,
        )
        operational_scenario.techniques.add(phishing_technique_fixture)

        data = OperationalScenarioReadSerializer(operational_scenario).data

        assert data["threats"] == []
        assert data["techniques"] == [
            {
                "str": "T1566.001 - Phishing: Spearphishing Attachment",
                "id": phishing_technique_fixture.id,
                "ref_id": "T1566.001",
            }
        ]
