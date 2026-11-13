import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Framework,
    Perimeter,
    RiskAssessment,
    Terminology,
    Threat,
)
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
    get_initial_meta,
)
from iam.models import Folder, User, UserGroup, UserGroupCodename
from pmbok.models import ResponsibilityMatrix
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

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_resets_status_and_workshop_progress(self):
        source = EbiosRMStudy.objects.get(name="test study")
        _build_full_study(source)
        source.status = EbiosRMStudy.Status.DONE
        source.update_workshop_step_status(1, 1, "done")  # saves source

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", version="2.0"
        )

        clone.refresh_from_db()
        assert clone.status == EbiosRMStudy.Status.PLANNED
        assert clone.meta == get_initial_meta()

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_does_not_copy_the_risk_assessment(self):
        # workshop 5 is left empty on the clone, regenerable from its scenarios
        _, clone, _ = self._clone()
        assert RiskAssessment.objects.filter(ebios_rm_study=clone).count() == 0

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_tolerates_out_of_study_references(self):
        source = EbiosRMStudy.objects.get(name="test study")
        _build_full_study(source)
        # the API does not forbid a child from pointing at another study's object
        other = EbiosRMStudy.objects.create(
            name="other study",
            risk_matrix=source.risk_matrix,
            folder=source.folder,
        )
        foreign_fe = FearedEvent.objects.create(name="foreign FE", ebios_rm_study=other)
        source_ro_to = RoTo.objects.get(ebios_rm_study=source)
        source_ro_to.feared_events.add(foreign_fe)

        # the id -> copy maps only hold the source study, so a direct lookup would
        # raise KeyError; the clone must fall back to the original instead.
        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", version="2.0"
        )

        clone_ro_to = RoTo.objects.get(ebios_rm_study=clone)
        assert foreign_fe in clone_ro_to.feared_events.all()
        assert clone_ro_to.feared_events.filter(ebios_rm_study=clone).count() == 2

    @pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
    def test_clone_into_another_domain_places_the_aggregate_there(self):
        source = EbiosRMStudy.objects.get(name="test study")
        _build_full_study(source)
        target = Folder.objects.create(
            name="target domain", parent_folder=source.folder
        )

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", version="2.0", folder=target
        )

        assert clone.folder == target
        # owned objects follow the study into the target folder (set in save())
        assert set(
            FearedEvent.objects.filter(ebios_rm_study=clone).values_list(
                "folder", flat=True
            )
        ) == {target.id}
        assert set(
            KillChain.objects.filter(
                operating_mode__operational_scenario__ebios_rm_study=clone
            ).values_list("folder", flat=True)
        ) == {target.id}
        # shared objects are carried over without raising (relinked or deep-copied
        # into the target domain by duplicate_related_objects)
        assert clone.assets.exists()


def _sibling_domains(**kwargs):
    root = Folder.get_root_folder()
    return [
        Folder.objects.create(
            name=name,
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
            **kwargs,
        )
        for name in ("domain A", "domain B")
    ]


def _study_in_domain(domain):
    """The full study, moved into `domain` with every shared object it uses, so
    that a sibling domain can see none of them."""
    source = EbiosRMStudy.objects.get(name="test study")
    refs = _build_full_study(source)
    source.folder = domain
    source.save()  # owned objects follow the study
    Asset.objects.update(folder=domain)
    Threat.objects.filter(id=refs["threat"].id).update(folder=domain)
    AppliedControl.objects.filter(id=refs["applied_control"].id).update(folder=domain)
    Entity.objects.filter(id=refs["entity"].id).update(folder=domain)
    ElementaryAction.objects.update(folder=domain)
    ElementaryAction.objects.filter(id=refs["ea_know"].id).update(threat=refs["threat"])
    # a primary asset whose supporting asset only reaches the scenario through
    # the parent link, as get_assets() walks it
    FearedEvent.objects.get(ebios_rm_study=source, ref_id="FE.01").assets.add(
        Asset.objects.get(name="Primary Asset 1")
    )
    source.refresh_from_db()
    return source, refs


def _clone_steps(study):
    return KillChain.objects.filter(
        operating_mode__operational_scenario__ebios_rm_study=study
    )


@pytest.mark.django_db
@pytest.mark.usefixtures("basic_ebios_rm_study_fixture")
class TestCloneStudyAcrossDomains:
    def test_shared_objects_the_target_cannot_see_are_copied_into_it(self):
        domain_a, domain_b = _sibling_domains()
        source, refs = _study_in_domain(domain_a)

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", folder=domain_b
        )

        assert set(clone.assets.values_list("folder", flat=True)) == {domain_b.id}
        assert {step.elementary_action.folder_id for step in _clone_steps(clone)} == {
            domain_b.id
        }
        stakeholder = Stakeholder.objects.get(ebios_rm_study=clone)
        assert stakeholder.entity.folder == domain_b
        assert stakeholder.applied_controls.get().folder == domain_b
        scenario = OperationalScenario.objects.get(ebios_rm_study=clone)
        threat_copy = scenario.threats.get()
        assert threat_copy.folder == domain_b
        # one copy per shared object: the copied action points at the same copy
        recon = _clone_steps(clone).get(elementary_action__name="Recon")
        assert recon.elementary_action.threat == threat_copy
        assert Threat.objects.filter(name="shared threat").count() == 2
        # the source keeps pointing at its own objects
        assert Stakeholder.objects.get(ebios_rm_study=source).entity == refs["entity"]
        assert (
            _clone_steps(source).get(elementary_action__name="Recon").elementary_action
            == (refs["ea_know"])
        )

    def test_copied_assets_keep_their_parents(self):
        domain_a, domain_b = _sibling_domains()
        source, _ = _study_in_domain(domain_a)

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", folder=domain_b
        )

        support = clone.assets.get(name="Supporting Asset 1")
        assert {(p.name, p.folder_id) for p in support.parent_assets.all()} == {
            ("Primary Asset 1", domain_b.id),
            ("Primary Asset 2", domain_b.id),
        }
        source_assets = OperationalScenario.objects.get(
            ebios_rm_study=source
        ).get_assets()
        clone_assets = OperationalScenario.objects.get(
            ebios_rm_study=clone
        ).get_assets()
        assert "Supporting Asset 1" in {asset.name for asset in clone_assets}
        assert sorted(a.name for a in clone_assets) == sorted(
            a.name for a in source_assets
        )

    def test_links_that_are_not_copied_are_dropped_when_invisible(self):
        domain_a, domain_b = _sibling_domains()
        source, _ = _study_in_domain(domain_a)
        framework = Framework.objects.create(
            name="FW", urn="urn:test:fw-clone", folder=Folder.get_root_folder()
        )
        audits = [
            ComplianceAssessment.objects.create(
                name=f"audit {domain.name}",
                framework=framework,
                folder=domain,
                perimeter=Perimeter.objects.create(
                    name=f"perimeter {domain.name}", folder=domain
                ),
            )
            for domain in (domain_a, domain_b)
        ]
        source.compliance_assessments.set(audits)
        source.responsibility_matrix = ResponsibilityMatrix.objects.create(
            name="RACI", folder=domain_a
        )
        source.save()

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", folder=domain_b
        )

        # audits and RACI are never copied: only what domain B can see is kept
        assert list(clone.compliance_assessments.all()) == [audits[1]]
        assert clone.responsibility_matrix is None
        assert source.compliance_assessments.count() == 2

    def test_objects_the_target_already_has_or_sees_are_reused(self):
        domain_a, domain_b = _sibling_domains()
        source, _ = _study_in_domain(domain_a)
        existing = ElementaryAction.objects.create(
            name="Recon",
            attack_stage=ElementaryAction.AttackStage.KNOW,
            folder=domain_b,
        )

        clone = duplicate_ebios_rm_study(
            source, name="test study (copy)", folder=domain_b
        )

        assert (
            _clone_steps(clone).get(elementary_action__name="Recon").elementary_action
            == existing
        )
        assert ElementaryAction.objects.filter(name="Recon").count() == 2
        # the built-in main entity is linked, never duplicated
        assert clone.reference_entity == source.reference_entity
        assert clone.reference_entity.builtin

    def test_endpoint_checks_add_permission_for_each_copied_type(self):
        startup(sender=None)
        domain_a, domain_b = _sibling_domains(create_iam_groups=True)
        for domain in (domain_a, domain_b):
            Folder.create_default_ug_and_ra(domain)
        source, refs = _study_in_domain(domain_a)
        analyst = User.objects.create_user(email="analyst@clone-tests.com")
        for domain in (domain_a, domain_b):
            UserGroup.objects.get(
                name=str(UserGroupCodename.ANALYST), folder=domain
            ).user_set.add(analyst)
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=analyst)[1]}"
        )
        url = f"/api/ebios-rm/studies/{source.id}/duplicate/"
        payload = {"name": "test study (copy)", "folder": str(domain_b.id)}

        # analysts may not add entities, and the stakeholder's entity is only
        # visible in domain A: copying it into domain B is refused, all rolled back
        response = client.post(url, payload, format="json")
        assert response.status_code == 403, response.content
        assert not EbiosRMStudy.objects.filter(name="test study (copy)").exists()
        assert not Asset.objects.filter(folder=domain_b).exists()

        # once domain B can see the entity, no entity needs to be created
        Entity.objects.filter(id=refs["entity"].id).update(folder=domain_b)
        response = client.post(url, payload, format="json")
        assert response.status_code == 200, response.content
        assert Asset.objects.filter(folder=domain_b).exists()


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
