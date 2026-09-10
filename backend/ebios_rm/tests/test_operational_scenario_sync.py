import pytest

from core.models import AppliedControl, RiskAssessment, Terminology
from ebios_rm.helpers import detect_sync_sources, sync_risk_assessment
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    FearedEvent,
    OperationalScenario,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from tprm.models import Entity

from ebios_rm.tests.fixtures import *


def _build_scenario_chain(study, *, attack_path_selected, operational_scenario_selected):
    """Build a full RO/TO -> strategic scenario -> attack path -> operational
    scenario chain, with a stakeholder + applied control hanging off the
    attack path (mirrors what workshop 3/4 produce)."""
    feared_event = FearedEvent.objects.create(
        name="test feared event", ebios_rm_study=study, is_selected=True
    )
    ro_to = RoTo.objects.create(
        ebios_rm_study=study,
        risk_origin=Terminology.objects.filter(
            field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN
        ).first(),
        target_objective="test target objective",
        is_selected=True,
    )
    ro_to.feared_events.add(feared_event)
    strategic_scenario = StrategicScenario.objects.create(
        name="test strategic scenario", ebios_rm_study=study, ro_to_couple=ro_to
    )
    attack_path = AttackPath.objects.create(
        name="test attack path",
        strategic_scenario=strategic_scenario,
        is_selected=attack_path_selected,
    )

    entity = Entity.objects.create(name="test entity")
    category = Terminology.objects.get(
        name="supplier", field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP
    )
    stakeholder = Stakeholder.objects.create(
        ebios_rm_study=study, entity=entity, category=category, is_selected=True
    )
    applied_control = AppliedControl.objects.create(name="test applied control")
    stakeholder.applied_controls.add(applied_control)
    attack_path.stakeholders.add(stakeholder)

    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study,
        attack_path=attack_path,
        likelihood=1,
        is_selected=operational_scenario_selected,
    )
    return operational_scenario


@pytest.mark.django_db
@pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
class TestOperationalScenarioSync:
    """Regression tests for CA-1821: a non-selected operational scenario must
    not leak into the synced risk assessment through a coarser sync level,
    just because its attack path is still selected from workshop 3."""

    def test_deselected_operational_scenario_is_not_synced(self):
        study = EbiosRMStudy.objects.get(name="test study")
        operational_scenario = _build_scenario_chain(
            study, attack_path_selected=True, operational_scenario_selected=False
        )

        sources = detect_sync_sources(study)

        assert sources is None

        risk_assessment = RiskAssessment.objects.create(
            name="test risk assessment",
            risk_matrix=study.risk_matrix,
            ebios_rm_study=study,
        )
        # Even if a caller ignored the None guard, syncing whatever sources
        # were found must not create a risk scenario for the deselected
        # operational scenario or drag its stakeholder's applied control in.
        sync_risk_assessment(risk_assessment, sources or {})

        assert risk_assessment.risk_scenarios.count() == 0
        assert operational_scenario.is_selected is False

    def test_selected_operational_scenario_is_synced(self):
        study = EbiosRMStudy.objects.get(name="test study")
        operational_scenario = _build_scenario_chain(
            study, attack_path_selected=True, operational_scenario_selected=True
        )

        sources = detect_sync_sources(study)

        assert sources is not None
        assert sources["operational_scenarios"] == [operational_scenario]
        assert sources["attack_paths"] == []
        assert sources["strategic_scenarios"] == []

        risk_assessment = RiskAssessment.objects.create(
            name="test risk assessment",
            risk_matrix=study.risk_matrix,
            ebios_rm_study=study,
        )
        sync_risk_assessment(risk_assessment, sources)

        assert risk_assessment.risk_scenarios.count() == 1
        risk_scenario = risk_assessment.risk_scenarios.first()
        assert risk_scenario.operational_scenario == operational_scenario
        assert (
            AppliedControl.objects.get(name="test applied control")
            in risk_scenario.existing_applied_controls.all()
        )

    def test_untouched_selected_attack_path_still_falls_back(self):
        """A hybrid study: one attack path was reviewed in workshop 4 and
        deselected there, another attack path was only selected in workshop 3
        and never got an operational scenario. The second one must still be
        picked up at the (coarser) attack-path sync level."""
        study = EbiosRMStudy.objects.get(name="test study")
        _build_scenario_chain(
            study, attack_path_selected=True, operational_scenario_selected=False
        )

        other_ro_to = RoTo.objects.create(
            ebios_rm_study=study,
            risk_origin=Terminology.objects.filter(
                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN
            ).first(),
            target_objective="other target objective",
            is_selected=True,
        )
        other_strategic_scenario = StrategicScenario.objects.create(
            name="other strategic scenario",
            ebios_rm_study=study,
            ro_to_couple=other_ro_to,
        )
        other_attack_path = AttackPath.objects.create(
            name="other attack path",
            strategic_scenario=other_strategic_scenario,
            is_selected=True,
        )

        sources = detect_sync_sources(study)

        assert sources is not None
        assert sources["operational_scenarios"] == []
        assert sources["attack_paths"] == [other_attack_path]
