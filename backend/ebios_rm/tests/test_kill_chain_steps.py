import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from rest_framework import status

from core.models import Asset, Terminology
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    ElementaryAction,
    KillChain,
    OperatingMode,
    OperationalScenario,
    RoTo,
    StrategicScenario,
)
from ebios_rm.serializers import (
    ElementaryActionWriteSerializer,
    KillChainReadSerializer,
    KillChainWriteSerializer,
)


def _operating_mode(study, name="test operating mode"):
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    ro_to = RoTo.objects.create(
        risk_origin=risk_origin,
        target_objective=f"target objective of {name}",
        ebios_rm_study=study,
    )
    strategic_scenario = StrategicScenario.objects.create(
        name=f"strategic scenario of {name}", ebios_rm_study=study, ro_to_couple=ro_to
    )
    attack_path = AttackPath.objects.create(
        name=f"attack path of {name}",
        ebios_rm_study=study,
        strategic_scenario=strategic_scenario,
    )
    operational_scenario = OperationalScenario.objects.create(
        ebios_rm_study=study, attack_path=attack_path
    )
    return OperatingMode.objects.create(
        name=name, operational_scenario=operational_scenario
    )


@pytest.fixture
def operating_mode_fixture(basic_ebios_rm_study_fixture):
    return _operating_mode(basic_ebios_rm_study_fixture)


@pytest.fixture
def supporting_assets_fixture():
    return (
        Asset.objects.create(name="HR mailbox", type=Asset.Type.SUPPORT),
        Asset.objects.create(name="R&D VPN", type=Asset.Type.SUPPORT),
    )


def _save_graph(client, operating_mode, steps, expected=status.HTTP_200_OK):
    response = client.post(
        f"/api/ebios-rm/operating-modes/{operating_mode.id}/save_graph/",
        {"kill_chain_steps": steps},
        format="json",
    )
    assert response.status_code == expected, response.content
    return response


@pytest.mark.django_db
class TestKillChainStepGraph:
    def test_new_steps_use_client_ids_for_antecedents(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, _ = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {"id": "new-1", "elementary_action": str(know.id)},
                {
                    "id": "new-2",
                    "elementary_action": str(enter.id),
                    "antecedents": ["new-1"],
                },
            ],
        )

        know_step = operating_mode_fixture.kill_chain_steps.get(elementary_action=know)
        enter_step = operating_mode_fixture.kill_chain_steps.get(
            elementary_action=enter
        )
        assert list(enter_step.antecedents.all()) == [know_step]
        assert list(know_step.successors.all()) == [enter_step]

    def test_existing_steps_keep_their_id_and_assets(
        self,
        admin_client,
        operating_mode_fixture,
        elementary_actions_fixture,
        supporting_assets_fixture,
    ):
        know, enter, _ = elementary_actions_fixture
        hr_mailbox, _ = supporting_assets_fixture
        know_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        know_step.assets.add(hr_mailbox)

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {
                    "id": str(know_step.id),
                    "elementary_action": str(know.id),
                    "position_x": 120,
                },
                {
                    "id": "new-1",
                    "elementary_action": str(enter.id),
                    "antecedents": [str(know_step.id)],
                },
            ],
        )

        know_step.refresh_from_db()
        assert know_step.position_x == 120
        assert list(know_step.assets.all()) == [hr_mailbox]
        assert operating_mode_fixture.kill_chain_steps.count() == 2

    def test_assets_are_set_and_cleared_when_sent(
        self,
        admin_client,
        operating_mode_fixture,
        elementary_actions_fixture,
        supporting_assets_fixture,
    ):
        know, _, _ = elementary_actions_fixture
        hr_mailbox, vpn = supporting_assets_fixture
        step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {
                    "id": str(step.id),
                    "elementary_action": str(know.id),
                    "assets": [str(hr_mailbox.id), str(vpn.id)],
                }
            ],
        )
        assert set(step.assets.all()) == {hr_mailbox, vpn}

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [{"id": str(step.id), "elementary_action": str(know.id), "assets": []}],
        )
        assert not step.assets.exists()

    def test_removed_steps_are_deleted(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, _ = elementary_actions_fixture
        kept = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [{"id": str(kept.id), "elementary_action": str(know.id)}],
        )

        assert list(operating_mode_fixture.kill_chain_steps.all()) == [kept]

    def test_same_action_can_appear_twice(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, _ = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {"id": "recon", "elementary_action": str(know.id)},
                {
                    "id": "phishing-hr",
                    "elementary_action": str(enter.id),
                    "antecedents": ["recon"],
                },
                {
                    "id": "phishing-rd",
                    "elementary_action": str(enter.id),
                    "antecedents": ["recon"],
                },
            ],
        )

        assert (
            operating_mode_fixture.kill_chain_steps.filter(
                elementary_action=enter
            ).count()
            == 2
        )

    def test_cycle_is_rejected(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        _, enter, _ = elementary_actions_fixture

        response = _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {"id": "a", "elementary_action": str(enter.id), "antecedents": ["b"]},
                {"id": "b", "elementary_action": str(enter.id), "antecedents": ["a"]},
            ],
            expected=status.HTTP_400_BAD_REQUEST,
        )

        assert any("cycle" in error for error in response.json()["errors"])

    def test_later_stage_antecedent_is_rejected(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        _, enter, exploit = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {"id": "x", "elementary_action": str(exploit.id)},
                {
                    "id": "e",
                    "elementary_action": str(enter.id),
                    "antecedents": ["x"],
                },
            ],
            expected=status.HTTP_400_BAD_REQUEST,
        )

    def test_unknown_asset_is_rejected(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, _, _ = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {
                    "id": "k",
                    "elementary_action": str(know.id),
                    "assets": ["00000000-0000-0000-0000-000000000000"],
                }
            ],
            expected=status.HTTP_400_BAD_REQUEST,
        )


@pytest.mark.django_db
class TestKillChainStepRatings:
    def test_save_graph_sets_ratings_only_when_sent(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, _, _ = elementary_actions_fixture
        step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {
                    "id": str(step.id),
                    "elementary_action": str(know.id),
                    "success_probability": 2,
                    "success_probability_pct": 65,
                    "technical_difficulty": 1,
                }
            ],
        )
        step.refresh_from_db()
        assert (
            step.success_probability,
            step.success_probability_pct,
            step.technical_difficulty,
        ) == (2, 65, 1)

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [{"id": str(step.id), "elementary_action": str(know.id)}],
        )
        step.refresh_from_db()
        assert (step.success_probability, step.success_probability_pct) == (2, 65)

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [
                {
                    "id": str(step.id),
                    "elementary_action": str(know.id),
                    "success_probability": -1,
                    "success_probability_pct": None,
                }
            ],
        )
        step.refresh_from_db()
        assert (step.success_probability, step.success_probability_pct) == (-1, None)

    @pytest.mark.parametrize(
        "rating",
        [
            {"success_probability": 4},
            {"technical_difficulty": -2},
            {"success_probability": "2"},
            {"success_probability_pct": 101},
            {"success_probability_pct": True},
        ],
    )
    def test_save_graph_rejects_out_of_range_ratings(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture, rating
    ):
        know, _, _ = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode_fixture,
            [{"id": "k", "elementary_action": str(know.id), **rating}],
            expected=status.HTTP_400_BAD_REQUEST,
        )

    def test_write_serializer_checks_level_against_matrix(
        self, operating_mode_fixture, elementary_actions_fixture
    ):
        know, _, _ = elementary_actions_fixture
        step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )

        assert KillChainWriteSerializer(
            step, data={"success_probability": 3}, partial=True
        ).is_valid()
        invalid = KillChainWriteSerializer(
            step, data={"success_probability": 4}, partial=True
        )
        assert not invalid.is_valid()
        assert "success_probability" in invalid.errors


@pytest.mark.django_db
class TestKillChainStepSerializers:
    def test_read_serializer_exposes_step_antecedents_and_assets(
        self,
        operating_mode_fixture,
        elementary_actions_fixture,
        supporting_assets_fixture,
    ):
        know, enter, _ = elementary_actions_fixture
        know_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        enter_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        enter_step.antecedents.add(know_step)
        enter_step.assets.add(supporting_assets_fixture[0])

        data = KillChainReadSerializer(enter_step).data

        assert [a["id"] for a in data["antecedents"]] == [know_step.id]
        assert [a["id"] for a in data["assets"]] == [supporting_assets_fixture[0].id]

    def test_antecedent_from_another_operating_mode_is_rejected(
        self,
        basic_ebios_rm_study_fixture,
        operating_mode_fixture,
        elementary_actions_fixture,
    ):
        know, enter, _ = elementary_actions_fixture
        other_mode = _operating_mode(basic_ebios_rm_study_fixture, "other mode")
        foreign_step = KillChain.objects.create(
            operating_mode=other_mode, elementary_action=know
        )

        serializer = KillChainWriteSerializer(
            data={
                "operating_mode": operating_mode_fixture.id,
                "elementary_action": enter.id,
                "antecedents": [foreign_step.id],
            }
        )

        assert not serializer.is_valid()
        assert "antecedents" in serializer.errors

    def test_descendant_as_antecedent_is_rejected(
        self, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, _ = elementary_actions_fixture
        first = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        second = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        second.antecedents.add(first)

        serializer = KillChainWriteSerializer(
            first, data={"antecedents": [second.id]}, partial=True
        )

        assert not serializer.is_valid()
        assert "antecedents" in serializer.errors

    def test_available_antecedents_filter(
        self, admin_client, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, exploit = elementary_actions_fixture
        know_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        enter_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        exploit_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=exploit
        )
        exploit_step.antecedents.add(enter_step)

        response = admin_client.get(
            f"/api/ebios-rm/kill-chains/?available_antecedents_for={enter_step.id}"
        )

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.json()["results"]}
        assert ids == {str(know_step.id)}


@pytest.mark.django_db(transaction=True)
def test_migration_converts_action_antecedents_to_steps(
    basic_ebios_rm_study_fixture, elementary_actions_fixture
):
    know, enter, _ = elementary_actions_fixture
    operating_mode = _operating_mode(basic_ebios_rm_study_fixture)

    executor = MigrationExecutor(connection)
    before = [("ebios_rm", "0027_operationalscenario_techniques")]
    after = [("ebios_rm", "0028_ebios_rm_label_readiness")]
    executor.migrate(before)
    apps = executor.loader.project_state(before).apps
    HistoricalKillChain = apps.get_model("ebios_rm", "KillChain")

    know_step = HistoricalKillChain.objects.create(
        operating_mode_id=operating_mode.id,
        elementary_action_id=know.id,
        folder_id=operating_mode.folder_id,
    )
    enter_step = HistoricalKillChain.objects.create(
        operating_mode_id=operating_mode.id,
        elementary_action_id=enter.id,
        folder_id=operating_mode.folder_id,
    )
    enter_step.antecedents.add(know.id)

    executor = MigrationExecutor(connection)
    executor.migrate(after)
    MigratedKillChain = executor.loader.project_state(after).apps.get_model(
        "ebios_rm", "KillChain"
    )
    migrated = MigratedKillChain.objects.get(id=enter_step.id)
    antecedent_ids = list(migrated.antecedents.values_list("id", flat=True))

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert antecedent_ids == [know_step.id]


@pytest.mark.django_db(transaction=True)
def test_migration_loses_no_antecedent_link(
    basic_ebios_rm_study_fixture, elementary_actions_fixture
):
    know, enter, exploit = elementary_actions_fixture
    operating_mode = _operating_mode(basic_ebios_rm_study_fixture)

    executor = MigrationExecutor(connection)
    before = [("ebios_rm", "0027_operationalscenario_techniques")]
    after = [("ebios_rm", "0028_ebios_rm_label_readiness")]
    executor.migrate(before)
    HistoricalKillChain = executor.loader.project_state(before).apps.get_model(
        "ebios_rm", "KillChain"
    )

    def step(action):
        return HistoricalKillChain.objects.create(
            operating_mode_id=operating_mode.id,
            elementary_action_id=action.id,
            folder_id=operating_mode.folder_id,
        )

    # the same action twice (uniqueness was only checked in clean()),
    # and a dangling antecedent whose step was deleted (exploit has none)
    know_step, know_again = step(know), step(know)
    enter_step = step(enter)
    enter_step.antecedents.add(know.id, exploit.id)

    executor = MigrationExecutor(connection)
    executor.migrate(after)
    MigratedKillChain = executor.loader.project_state(after).apps.get_model(
        "ebios_rm", "KillChain"
    )
    migrated = MigratedKillChain.objects.get(id=enter_step.id)
    antecedents = set(migrated.antecedents.values_list("id", flat=True))
    legacy = set(migrated.legacy_antecedent_actions.values_list("id", flat=True))

    executor = MigrationExecutor(connection)
    executor.migrate(before)
    RolledBack = executor.loader.project_state(before).apps.get_model(
        "ebios_rm", "KillChain"
    )
    restored = set(
        RolledBack.objects.get(id=enter_step.id).antecedents.values_list(
            "id", flat=True
        )
    )

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert antecedents == {know_step.id, know_again.id}
    assert legacy == {know.id, exploit.id}
    assert restored == {know.id, exploit.id}


@pytest.mark.django_db
def test_switching_method_keeps_typed_operating_mode_likelihood(
    basic_ebios_rm_study_fixture, elementary_actions_fixture
):
    study = basic_ebios_rm_study_fixture
    know, _, _ = elementary_actions_fixture
    operating_mode = _operating_mode(study)
    operating_mode.likelihood = 2
    operating_mode.save()
    KillChain.objects.create(
        operating_mode=operating_mode, elementary_action=know, success_probability=0
    )

    study.quotation_method = EbiosRMStudy.QuotationMethod.STANDARD
    study.save()
    operating_mode.refresh_from_db()
    assert operating_mode.likelihood == 2
    assert (
        operating_mode.effective_likelihood == operating_mode.computed_likelihood == 0
    )

    study.quotation_method = EbiosRMStudy.QuotationMethod.EXPRESS
    study.save()
    operating_mode.refresh_from_db()
    assert operating_mode.effective_likelihood == 2


@pytest.mark.django_db
class TestReviewFixes:
    def test_changing_attack_stage_of_a_used_action_is_checked(
        self, operating_mode_fixture, elementary_actions_fixture
    ):
        know, enter, exploit = elementary_actions_fixture
        know_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        enter_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        enter_step.antecedents.add(know_step)

        serializer = ElementaryActionWriteSerializer(
            know,
            data={"attack_stage": ElementaryAction.AttackStage.EXPLOIT},
            partial=True,
        )
        assert not serializer.is_valid()

        serializer = ElementaryActionWriteSerializer(
            exploit,
            data={"attack_stage": ElementaryAction.AttackStage.KNOW},
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors

    def test_know_step_accepts_a_know_antecedent(
        self, operating_mode_fixture, elementary_actions_fixture
    ):
        know, _, _ = elementary_actions_fixture
        first = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        serializer = KillChainWriteSerializer(
            data={
                "operating_mode": operating_mode_fixture.id,
                "elementary_action": know.id,
                "antecedents": [first.id],
            }
        )
        assert serializer.is_valid(), serializer.errors

    def test_changing_a_step_rechecks_its_kept_links(
        self,
        basic_ebios_rm_study_fixture,
        operating_mode_fixture,
        elementary_actions_fixture,
    ):
        know, enter, exploit = elementary_actions_fixture
        enter_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=enter
        )
        exploit_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=exploit
        )
        exploit_step.antecedents.add(enter_step)

        serializer = KillChainWriteSerializer(
            exploit_step, data={"elementary_action": know.id}, partial=True
        )
        assert not serializer.is_valid()
        assert "antecedents" in serializer.errors

        know_step = KillChain.objects.create(
            operating_mode=operating_mode_fixture, elementary_action=know
        )
        enter_step.antecedents.add(know_step)
        serializer = KillChainWriteSerializer(
            know_step, data={"elementary_action": exploit.id}, partial=True
        )
        assert not serializer.is_valid()
        assert "elementary_action" in serializer.errors

        other_mode = _operating_mode(basic_ebios_rm_study_fixture, "other mode")
        serializer = KillChainWriteSerializer(
            enter_step, data={"operating_mode": other_mode.id}, partial=True
        )
        assert not serializer.is_valid()
        assert "operating_mode" in serializer.errors

    def test_smaller_matrix_clamps_step_ratings(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        from core.models import RiskMatrix, StoredLibrary

        study = basic_ebios_rm_study_fixture
        study.quotation_method = EbiosRMStudy.QuotationMethod.ADVANCED
        study.save()
        know, _, _ = elementary_actions_fixture
        operating_mode = _operating_mode(study)
        step = KillChain.objects.create(
            operating_mode=operating_mode,
            elementary_action=know,
            success_probability=3,
            technical_difficulty=3,
        )
        StoredLibrary.objects.get(
            urn="urn:intuitem:risk:library:risk-matrix-3x3-mult"
        ).load()

        study.risk_matrix = RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:3x3-mult"
        )
        study.save()

        step.refresh_from_db()
        operating_mode.refresh_from_db()
        assert (step.success_probability, step.technical_difficulty) == (2, 2)
        assert 0 <= operating_mode.computed_likelihood <= 2

    def test_smaller_matrix_clamps_express_likelihoods(
        self, basic_ebios_rm_study_fixture
    ):
        from core.models import RiskMatrix, StoredLibrary

        study = basic_ebios_rm_study_fixture
        study.quotation_method = EbiosRMStudy.QuotationMethod.EXPRESS
        study.save()
        operating_mode = _operating_mode(study)
        operating_mode.likelihood = 3
        operating_mode.save()
        StoredLibrary.objects.get(
            urn="urn:intuitem:risk:library:risk-matrix-3x3-mult"
        ).load()

        study.risk_matrix = RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:3x3-mult"
        )
        study.save()

        operating_mode.refresh_from_db()
        scenario = operating_mode.operational_scenario
        scenario.refresh_from_db()
        assert operating_mode.likelihood == 2
        assert scenario.likelihood == 2
        assert scenario.get_likelihood_display()

    def test_failed_recompute_rolls_back_the_matrix_change(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture, monkeypatch
    ):
        from core.models import RiskMatrix, StoredLibrary

        study = basic_ebios_rm_study_fixture
        study.quotation_method = EbiosRMStudy.QuotationMethod.ADVANCED
        study.save()
        know, _, _ = elementary_actions_fixture
        step = KillChain.objects.create(
            operating_mode=_operating_mode(study),
            elementary_action=know,
            success_probability=3,
            technical_difficulty=3,
        )
        StoredLibrary.objects.get(
            urn="urn:intuitem:risk:library:risk-matrix-3x3-mult"
        ).load()
        original_matrix = study.risk_matrix_id

        def fail(*args, **kwargs):
            raise RuntimeError

        monkeypatch.setattr(OperatingMode, "save", fail)
        study.risk_matrix = RiskMatrix.objects.get(
            urn="urn:intuitem:risk:matrix:3x3-mult"
        )
        with pytest.raises(RuntimeError):
            study.save()

        step.refresh_from_db()
        assert (step.success_probability, step.technical_difficulty) == (3, 3)
        assert EbiosRMStudy.objects.get(id=study.id).risk_matrix_id == original_matrix

    def test_refresh_ratings_follows_a_changed_matrix(
        self, basic_ebios_rm_study_fixture
    ):
        from ebios_rm import rating_kit

        study = basic_ebios_rm_study_fixture
        ro_to = _operating_mode(
            study
        ).operational_scenario.attack_path.strategic_scenario.ro_to_couple
        ro_to.motivation, ro_to.resources = 4, 4
        ro_to.save()
        before = ro_to.pertinence

        matrix = study.risk_matrix
        section = rating_kit.default_section(len(matrix.json_definition["probability"]))
        section["ro_to"]["pertinence_grid"] = [[0] * 4 for _ in range(4)]
        matrix.json_definition = {**matrix.json_definition, "ebios_rm": section}
        matrix.save()

        EbiosRMStudy.objects.get(id=study.id).refresh_ratings()
        ro_to.refresh_from_db()
        assert ro_to.pertinence != before
        assert ro_to.pertinence == rating_kit.pertinence(
            rating_kit.resolve(matrix.json_definition)["ro_to"], 4, 4
        )


def _domain_client(email, folder, role="BI-RL-ANA"):
    """A user holding one built-in role on `folder` only, with an API client."""
    from knox.models import AuthToken
    from rest_framework.test import APIClient

    from iam.models import Folder, Role, RoleAssignment, User, UserGroup

    user = User.objects.create_user(email=email, is_published=True)
    group = UserGroup.objects.create(name=f"group of {email}", folder=folder)
    group.user_set.add(user)
    RoleAssignment.objects.create(
        user_group=group,
        role=Role.objects.get(name=role),
        folder=Folder.get_root_folder(),
        is_recursive=True,
    ).perimeter_folders.add(folder)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


@pytest.mark.django_db
class TestSaveGraphHiddenAssets:
    """An analyst of the study's domain edits steps linked to another domain's assets."""

    @pytest.fixture
    def scoped(self, admin_client, ebios_rm_matrix_fixture):
        from iam.models import Folder

        root = Folder.get_root_folder()
        study_domain, other_domain = (
            Folder.objects.create(
                name=name, parent_folder=root, content_type=Folder.ContentType.DOMAIN
            )
            for name in ("Study domain", "Other domain")
        )
        study = EbiosRMStudy.objects.create(
            name="scoped study",
            risk_matrix=ebios_rm_matrix_fixture,
            folder=study_domain,
        )
        operating_mode = _operating_mode(study)
        action = ElementaryAction.objects.create(
            name="Phishing",
            attack_stage=ElementaryAction.AttackStage.ENTER,
            folder=study_domain,
        )
        visible = Asset.objects.create(
            name="Visible", type=Asset.Type.SUPPORT, folder=study_domain
        )
        hidden = Asset.objects.create(
            name="Hidden", type=Asset.Type.SUPPORT, folder=other_domain
        )
        linked = KillChain.objects.create(
            operating_mode=operating_mode, elementary_action=action
        )
        linked.assets.set([visible, hidden])
        other = KillChain.objects.create(
            operating_mode=operating_mode, elementary_action=action
        )
        return {
            "client": _domain_client(
                "analyst@kill-chain-steps-tests.com", study_domain
            ),
            "study": study,
            "operating_mode": operating_mode,
            "action": action,
            "visible": visible,
            "hidden": hidden,
            "linked": linked,
            "other": other,
        }

    def _step(self, scoped, step, assets):
        return {
            "id": str(step.id),
            "elementary_action": str(scoped["action"].id),
            "antecedents": [],
            "assets": [str(asset.id) for asset in assets],
        }

    def test_graph_save_keeps_assets_the_user_cannot_view(self, scoped):
        client, operating_mode = scoped["client"], scoped["operating_mode"]
        listing = client.get(
            f"/api/ebios-rm/kill-chains/?operating_mode={operating_mode.id}"
        )
        assert listing.status_code == status.HTTP_200_OK
        # Rebuild the payload as the graph editor does: entries without an id are skipped
        steps = [
            {
                "id": row["id"],
                "elementary_action": row["elementary_action"]["id"],
                "antecedents": [],
                "assets": [a["id"] for a in row["assets"] if a.get("id")],
            }
            for row in listing.json()["results"]
        ]
        _save_graph(client, operating_mode, steps)

        assert set(scoped["linked"].assets.all()) == {
            scoped["visible"],
            scoped["hidden"],
        }

    def test_graph_save_leaving_a_hidden_asset_out_keeps_it(self, scoped):
        _save_graph(
            scoped["client"],
            scoped["operating_mode"],
            [
                self._step(scoped, scoped["linked"], [scoped["visible"]]),
                self._step(scoped, scoped["other"], []),
            ],
        )
        assert set(scoped["linked"].assets.all()) == {
            scoped["visible"],
            scoped["hidden"],
        }

    def test_hidden_asset_cannot_be_linked_to_another_step(self, scoped):
        _save_graph(
            scoped["client"],
            scoped["operating_mode"],
            [
                self._step(scoped, scoped["linked"], [scoped["visible"]]),
                self._step(scoped, scoped["other"], [scoped["hidden"]]),
            ],
            expected=status.HTTP_400_BAD_REQUEST,
        )
        assert not scoped["other"].assets.exists()

    def test_hidden_asset_cannot_follow_a_step_id_into_another_mode(self, scoped):
        """A step id from another operating mode is a new step there, with no links."""
        target = _operating_mode(scoped["study"], "another operating mode")
        _save_graph(
            scoped["client"],
            target,
            [self._step(scoped, scoped["linked"], [scoped["hidden"]])],
            expected=status.HTTP_400_BAD_REQUEST,
        )
        assert not target.kill_chain_steps.exists()


@pytest.mark.django_db
def test_moving_a_step_recomputes_both_operating_modes(
    admin_client, basic_ebios_rm_study_fixture, elementary_actions_fixture
):
    study = basic_ebios_rm_study_fixture
    study.quotation_method = "standard"
    study.save()
    source = _operating_mode(study, "source mode")
    target = _operating_mode(study, "target mode")
    step = KillChain.objects.create(
        operating_mode=source,
        elementary_action=elementary_actions_fixture[0],
        success_probability=2,
    )
    source.refresh_likelihood()
    source.refresh_from_db()
    assert source.computed_likelihood == 2

    response = admin_client.patch(
        f"/api/ebios-rm/kill-chains/{step.id}/",
        {"operating_mode": str(target.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.content
    source.refresh_from_db()
    target.refresh_from_db()
    assert source.computed_likelihood == -1
    assert target.computed_likelihood == 2


@pytest.mark.django_db(transaction=True)
def test_migration_breaks_loops_between_steps(
    basic_ebios_rm_study_fixture, elementary_actions_fixture
):
    from datetime import timedelta

    know, enter, _ = elementary_actions_fixture
    # Before 0028, two actions of one stage could each be the other's antecedent
    pivot = ElementaryAction.objects.create(
        name="Pivot", attack_stage=ElementaryAction.AttackStage.ENTER
    )
    operating_mode = _operating_mode(basic_ebios_rm_study_fixture)

    executor = MigrationExecutor(connection)
    before = [("ebios_rm", "0027_operationalscenario_techniques")]
    after = [("ebios_rm", "0028_ebios_rm_label_readiness")]
    executor.migrate(before)
    HistoricalKillChain = executor.loader.project_state(before).apps.get_model(
        "ebios_rm", "KillChain"
    )

    def step(action, minutes):
        created = HistoricalKillChain.objects.create(
            operating_mode_id=operating_mode.id,
            elementary_action_id=action.id,
            folder_id=operating_mode.folder_id,
        )
        HistoricalKillChain.objects.filter(id=created.id).update(
            created_at=created.created_at + timedelta(minutes=minutes)
        )
        return created

    older, newer, latest = step(enter, 1), step(pivot, 2), step(know, 3)
    older.antecedents.add(pivot.id, know.id)  # a newer antecedent, outside any loop
    newer.antecedents.add(enter.id)

    executor = MigrationExecutor(connection)
    executor.migrate(after)
    MigratedKillChain = executor.loader.project_state(after).apps.get_model(
        "ebios_rm", "KillChain"
    )
    antecedents = {
        step.id: set(
            MigratedKillChain.objects.get(id=step.id).antecedents.values_list(
                "id", flat=True
            )
        )
        for step in (older, newer)
    }
    legacy = set(
        MigratedKillChain.objects.get(
            id=older.id
        ).legacy_antecedent_actions.values_list("id", flat=True)
    )

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    # The older step stays the antecedent of the newer one
    assert antecedents == {older.id: {latest.id}, newer.id: {older.id}}
    assert legacy == {pivot.id, know.id}


@pytest.mark.django_db(transaction=True)
def test_migration_fills_pertinence_as_before(basic_ebios_rm_study_fixture):
    risk_origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    # (motivation, resources): pertinence from the matrix used before 0028
    expected = {(0, 3): 0, (1, 1): 1, (1, 4): 2, (2, 3): 3, (3, 1): 2, (4, 4): 4}
    couples = {
        key: RoTo.objects.create(
            ebios_rm_study=basic_ebios_rm_study_fixture,
            risk_origin=risk_origin,
            target_objective=f"objective {key}",
            motivation=key[0],
            resources=key[1],
        )
        for key in expected
    }

    executor = MigrationExecutor(connection)
    executor.migrate([("ebios_rm", "0027_operationalscenario_techniques")])
    after = [("ebios_rm", "0028_ebios_rm_label_readiness")]
    executor = MigrationExecutor(connection)
    executor.migrate(after)
    MigratedRoTo = executor.loader.project_state(after).apps.get_model(
        "ebios_rm", "RoTo"
    )
    pertinence = {
        key: MigratedRoTo.objects.get(id=ro_to.id).pertinence
        for key, ro_to in couples.items()
    }

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert pertinence == expected
