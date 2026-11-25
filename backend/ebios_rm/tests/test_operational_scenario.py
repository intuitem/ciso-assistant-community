import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Asset, Terminology, Threat
from ebios_rm.models import (
    AttackPath,
    FearedEvent,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from ebios_rm.serializers import OperationalScenarioReadSerializer
from sec_intel.models import Technique


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


@pytest.mark.django_db
class TestOperationalScenarioGetAssets:
    def _scenario(self, study, attack_path, feared_events):
        attack_path.ro_to_couple.feared_events.set(feared_events)
        return OperationalScenario.objects.create(
            ebios_rm_study=study, attack_path=attack_path
        )

    def _feared_event(self, study, name, assets):
        fe = FearedEvent.objects.create(
            name=name, ebios_rm_study=study, is_selected=True
        )
        fe.assets.set(assets)
        return fe

    def test_returns_seeds_and_all_descendants_once(
        self, basic_ebios_rm_study_fixture, basic_attack_path_fixture
    ):
        study = basic_ebios_rm_study_fixture
        p1 = Asset.objects.get(name="Primary Asset 1")
        p2 = Asset.objects.get(name="Primary Asset 2")
        support = Asset.objects.get(name="Supporting Asset 1")
        grandchild = Asset.objects.create(name="Grandchild", type=Asset.Type.SUPPORT)
        grandchild.parent_assets.add(support)
        # p1 reached through two feared events: the join yields duplicate rows
        fe_a = self._feared_event(study, "fe a", [p1])
        fe_b = self._feared_event(study, "fe b", [p1, p2])
        unselected = FearedEvent.objects.create(name="fe off", ebios_rm_study=study)
        unselected.assets.add(Asset.objects.create(name="Not selected"))
        scenario = self._scenario(
            study, basic_attack_path_fixture, [fe_a, fe_b, unselected]
        )

        assert sorted(a.name for a in scenario.get_assets()) == sorted(
            ["Primary Asset 1", "Primary Asset 2", "Supporting Asset 1", "Grandchild"]
        )

    def test_query_count_does_not_grow_with_the_graph(
        self, basic_ebios_rm_study_fixture, basic_attack_path_fixture
    ):
        study = basic_ebios_rm_study_fixture
        seeds = list(Asset.objects.filter(name__startswith="Primary"))
        scenario = self._scenario(
            study,
            basic_attack_path_fixture,
            [self._feared_event(study, "fe", seeds)],
        )

        def count():
            with CaptureQueriesContext(connection) as ctx:
                list(scenario.get_assets())
            return len(ctx.captured_queries)

        small = count()
        fe = FearedEvent.objects.get(name="fe")
        for i in range(10):
            primary = Asset.objects.create(name=f"extra primary {i}")
            child = Asset.objects.create(
                name=f"extra child {i}", type=Asset.Type.SUPPORT
            )
            child.parent_assets.add(primary)
            fe.assets.add(primary)

        assert count() == small
