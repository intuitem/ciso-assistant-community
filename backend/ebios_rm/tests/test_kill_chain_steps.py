import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from iam.models import User, UserGroup
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.apps import startup
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

from ebios_rm.tests.fixtures import *


@pytest.fixture
def admin_client():
    startup(sender=None)
    admin = User.objects.create_superuser("admin@kill-chain-steps-tests.com")
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)
    client = APIClient()
    token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token[1]}")
    return client


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
def elementary_actions_fixture():
    know = ElementaryAction.objects.create(
        name="Reconnaissance", attack_stage=ElementaryAction.AttackStage.KNOW
    )
    enter = ElementaryAction.objects.create(
        name="Phishing", attack_stage=ElementaryAction.AttackStage.ENTER
    )
    exploit = ElementaryAction.objects.create(
        name="Exfiltration", attack_stage=ElementaryAction.AttackStage.EXPLOIT
    )
    return know, enter, exploit


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
