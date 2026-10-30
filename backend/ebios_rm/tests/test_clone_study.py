import pytest

from core.models import AppliedControl, Asset, Terminology, Threat
from ebios_rm.helpers import duplicate_ebios_rm_study
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    ElementaryAction,
    FearedEvent,
    KillChain,
    OperatingMode,
    OperationalScenario,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from tprm.models import Entity


def _build_full_study(study):
    """Build a complete graph (feared events -> ... -> kill chains) with
    antecedents, forced ratings and shared references, like workshops 1-4
    produce. Returns the objects a clone test needs to compare against."""
    study.quotation_method = EbiosRMStudy.QuotationMethod.STANDARD
    study.save()

    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    category, _ = Terminology.objects.get_or_create(
        name="supplier",
        field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
        defaults={"is_visible": True},
    )

    asset = Asset.objects.create(name="shared asset", type=Asset.Type.SUPPORT)
    threat = Threat.objects.create(name="shared threat")
    applied_control = AppliedControl.objects.create(name="shared control")
    entity = Entity.objects.create(name="shared entity")
    ea_know = ElementaryAction.objects.create(
        name="Recon", attack_stage=ElementaryAction.AttackStage.KNOW
    )
    ea_enter = ElementaryAction.objects.create(
        name="Phishing", attack_stage=ElementaryAction.AttackStage.ENTER
    )

    fe1 = FearedEvent.objects.create(
        name="FE 1", ref_id="FE.01", gravity=2, is_selected=True, ebios_rm_study=study
    )
    fe1.assets.add(asset)
    fe2 = FearedEvent.objects.create(
        name="FE 2", ref_id="FE.02", gravity=1, ebios_rm_study=study
    )

    ro_to = RoTo.objects.create(
        ebios_rm_study=study,
        risk_origin=risk_origin,
        target_objective="steal the crown jewels",
        is_selected=True,
    )
    ro_to.feared_events.set([fe1, fe2])

    stakeholder = Stakeholder.objects.create(
        ebios_rm_study=study, entity=entity, category=category, is_selected=True
    )
    stakeholder.applied_controls.add(applied_control)

    strategic_scenario = StrategicScenario.objects.create(
        name="SS 1",
        ref_id="SS.01",
        ebios_rm_study=study,
        ro_to_couple=ro_to,
        focused_feared_event=fe1,
        gravity_forced=3,
    )
    attack_path = AttackPath.objects.create(
        name="AP 1",
        ref_id="AP.01",
        strategic_scenario=strategic_scenario,
        is_selected=True,
    )
    attack_path.stakeholders.add(stakeholder)

    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study, attack_path=attack_path, is_selected=True
    )
    operational_scenario.threats.add(threat)

    operating_mode = OperatingMode.objects.create(
        name="MO 1",
        ref_id="MO.01",
        operational_scenario=operational_scenario,
        graph_columns={"stage-col-0": {"x": 0, "y": 0, "width": 200, "height": 100}},
    )
    step_know = KillChain.objects.create(
        operating_mode=operating_mode,
        elementary_action=ea_know,
        success_probability=2,
        technical_difficulty=1,
        position_x=10,
        position_y=20,
    )
    step_enter = KillChain.objects.create(
        operating_mode=operating_mode,
        elementary_action=ea_enter,
        success_probability=3,
        technical_difficulty=2,
        is_highlighted=True,
    )
    step_enter.antecedents.add(step_know)
    step_enter.assets.add(asset)

    # settle the source ratings the same way the clone will
    study.save()
    operating_mode.refresh_from_db()

    return {
        "asset": asset,
        "threat": threat,
        "applied_control": applied_control,
        "entity": entity,
        "ea_know": ea_know,
        "operating_mode": operating_mode,
        "step_know": step_know,
        "step_enter": step_enter,
    }


@pytest.mark.django_db
class TestCloneStudy:
    def _clone(self):
        source = EbiosRMStudy.objects.get(name="test study")
        refs = _build_full_study(source)
        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", version="2.0"
        )
        return source, clone, refs

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_copies_the_whole_graph(self):
        _, clone, _ = self._clone()

        assert FearedEvent.objects.filter(ebios_rm_study=clone).count() == 2
        assert RoTo.objects.filter(ebios_rm_study=clone).count() == 1
        assert Stakeholder.objects.filter(ebios_rm_study=clone).count() == 1
        assert StrategicScenario.objects.filter(ebios_rm_study=clone).count() == 1
        assert AttackPath.objects.filter(ebios_rm_study=clone).count() == 1
        assert OperationalScenario.objects.filter(ebios_rm_study=clone).count() == 1
        assert (
            OperatingMode.objects.filter(
                operational_scenario__ebios_rm_study=clone
            ).count()
            == 1
        )
        assert (
            KillChain.objects.filter(
                operating_mode__operational_scenario__ebios_rm_study=clone
            ).count()
            == 2
        )

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_remaps_intra_study_relations(self):
        _, clone, _ = self._clone()

        ro_to = RoTo.objects.get(ebios_rm_study=clone)
        assert set(ro_to.feared_events.values_list("ebios_rm_study", flat=True)) == {
            clone.id
        }
        strategic_scenario = StrategicScenario.objects.get(ebios_rm_study=clone)
        assert strategic_scenario.ro_to_couple == ro_to
        assert strategic_scenario.focused_feared_event.ebios_rm_study == clone
        attack_path = AttackPath.objects.get(ebios_rm_study=clone)
        assert attack_path.strategic_scenario == strategic_scenario
        assert set(
            attack_path.stakeholders.values_list("ebios_rm_study", flat=True)
        ) == {clone.id}
        operational_scenario = OperationalScenario.objects.get(ebios_rm_study=clone)
        assert operational_scenario.attack_path == attack_path

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_remaps_kill_chain_antecedents(self):
        _, clone, _ = self._clone()

        steps = KillChain.objects.filter(
            operating_mode__operational_scenario__ebios_rm_study=clone
        )
        enter = steps.get(is_highlighted=True)
        antecedents = list(enter.antecedents.all())
        assert len(antecedents) == 1
        # antecedent is a cloned step, not the source one
        assert antecedents[0] in steps

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_references_shared_objects(self):
        _, clone, refs = self._clone()

        feared_event = FearedEvent.objects.get(ebios_rm_study=clone, ref_id="FE.01")
        assert list(feared_event.assets.all()) == [refs["asset"]]
        stakeholder = Stakeholder.objects.get(ebios_rm_study=clone)
        assert stakeholder.entity == refs["entity"]
        assert list(stakeholder.applied_controls.all()) == [refs["applied_control"]]
        operational_scenario = OperationalScenario.objects.get(ebios_rm_study=clone)
        assert list(operational_scenario.threats.all()) == [refs["threat"]]
        enter = KillChain.objects.get(
            operating_mode__operational_scenario__ebios_rm_study=clone,
            is_highlighted=True,
        )
        assert list(enter.assets.all()) == [refs["asset"]]
        know = KillChain.objects.get(
            operating_mode__operational_scenario__ebios_rm_study=clone,
            is_highlighted=False,
        )
        assert know.elementary_action == refs["ea_know"]

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_copies_inputs_and_matches_computed_ratings(self):
        _, clone, refs = self._clone()

        strategic_scenario = StrategicScenario.objects.get(ebios_rm_study=clone)
        assert strategic_scenario.gravity_forced == 3

        know = KillChain.objects.get(
            operating_mode__operational_scenario__ebios_rm_study=clone,
            is_highlighted=False,
        )
        assert (know.position_x, know.position_y) == (10, 20)
        assert know.success_probability == 2

        clone_mode = OperatingMode.objects.get(
            operational_scenario__ebios_rm_study=clone
        )
        assert clone_mode.graph_columns == refs["operating_mode"].graph_columns
        assert (
            clone_mode.computed_likelihood == refs["operating_mode"].computed_likelihood
        )

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_deleting_source_leaves_clone_intact(self):
        source, clone, _ = self._clone()
        source.delete()

        enter = KillChain.objects.get(
            operating_mode__operational_scenario__ebios_rm_study=clone,
            is_highlighted=True,
        )
        assert enter.antecedents.count() == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
class TestCloneStudyEndpoint:
    def test_duplicate_endpoint_returns_the_new_study(self, admin_client):
        study = EbiosRMStudy.objects.get(name="test study")
        response = admin_client.post(
            f"/api/ebios-rm/studies/{study.id}/duplicate/",
            {"name": "test study (copy)", "version": "2.0"},
            format="json",
        )
        assert response.status_code == 200, response.content
        new_id = response.json()["results"]["id"]
        assert EbiosRMStudy.objects.filter(id=new_id).exists()
        assert new_id != str(study.id)

    def test_duplicate_into_same_folder_with_same_name_is_rejected(self, admin_client):
        study = EbiosRMStudy.objects.get(name="test study")
        response = admin_client.post(
            f"/api/ebios-rm/studies/{study.id}/duplicate/",
            {"name": "test study"},
            format="json",
        )
        assert response.status_code == 400, response.content
