from types import SimpleNamespace

import pytest

from chat.workflows.ebios_facilitation import _find, _readable, _roto_label


def test_find_compound_name_by_its_first_part():
    by_name = {
        "rançongiciel via hôpisoft - accès via hôpisoft": 1,
        "fuite de données - accès direct": 2,
    }
    assert _find(by_name, "Rançongiciel via Hôpisoft") == 1
    assert _find(by_name, "inconnu") is None


def test_find_first_part_must_be_unique():
    by_name = {"risque a - chemin 1": 1, "risque a - chemin 2": 2}
    assert _find(by_name, "risque a") is None


def test_couple_shown_in_user_language():
    origin = SimpleNamespace(name="organized_crime", translations={})
    roto = SimpleNamespace(risk_origin=origin, target_objective="extorquer")
    assert _roto_label(roto, "fr") == "crime organisé - extorquer"
    assert (
        _readable(
            "risk_origin", "Organized_crime", {}, {"organized_crime": "crime organisé"}
        )
        == "crime organisé"
    )


def test_objects_of_the_current_proposal_match_by_exact_name_only():
    from datetime import datetime, timedelta, timezone

    from chat.workflows.ebios_facilitation import _BATCH_START

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    fresh = SimpleNamespace(created_at=start + timedelta(seconds=1))
    old = SimpleNamespace(created_at=start - timedelta(days=1))
    token = _BATCH_START.set(start)
    try:
        assert (
            _find({"vengeur → fuite de données": fresh}, "activiste → fuite de données")
            is None
        )
        assert (
            _find({"vengeur → fuite de données": fresh}, "Vengeur → fuite de données")
            is fresh
        )
        assert (
            _find({"vengeur → fuite de donnée": old}, "vengeur → fuite de données")
            is old
        )
    finally:
        _BATCH_START.reset(token)


def _study_with_couples():
    from core.models import RiskMatrix, Terminology
    from ebios_rm.models import EbiosRMStudy, FearedEvent, RoTo
    from iam.models import Folder
    from test_fixtures import RISK_MATRIX_JSON_DEFINITION

    folder = Folder.objects.create(
        name="d",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    matrix = RiskMatrix.objects.create(
        name="m",
        folder=folder,
        is_enabled=True,
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    study = EbiosRMStudy.objects.create(name="s", folder=folder, risk_matrix=matrix)
    origin, _ = Terminology.objects.get_or_create(
        name="state",
        field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
        defaults={"is_visible": True},
    )
    a, b = (
        RoTo.objects.create(
            ebios_rm_study=study, risk_origin=origin, target_objective=o, motivation=4
        )
        for o in ("spy", "steal")
    )
    fe_a, fe_b = (
        FearedEvent.objects.create(ebios_rm_study=study, name=n)
        for n in ("leak", "outage")
    )
    a.feared_events.add(fe_a)
    b.feared_events.add(fe_b)
    return study, a, b, fe_a


def _workflow_ctx():
    from chat.workflows.ebios_rm_assist import EbiosRMAssistWorkflow

    scope = SimpleNamespace(queryset=lambda model: model.objects.all())
    return EbiosRMAssistWorkflow(), SimpleNamespace(scope=scope)


@pytest.mark.django_db
def test_reconfirmed_couple_keeps_the_ratings_the_proposal_omits():
    study, a, _, _ = _study_with_couples()
    workflow, ctx = _workflow_ctx()
    item = {"risk_origin": "state", "target_objective": "spy", "resources": 2}
    assert workflow._record_rotos(ctx, study, item)
    a.refresh_from_db()
    assert (a.motivation, a.resources) == (4, 2)


@pytest.mark.django_db
def test_strategic_scenario_keeps_its_own_paths_and_couple_events():
    from ebios_rm.models import AttackPath, StrategicScenario

    study, a, b, fe_a = _study_with_couples()
    other = StrategicScenario.objects.create(
        ebios_rm_study=study, name="other", ro_to_couple=a
    )
    shared = AttackPath.objects.create(
        ebios_rm_study=study, strategic_scenario=other, name="supplier access"
    )
    workflow, ctx = _workflow_ctx()
    item = {
        "name": "theft",
        "roto": 2,
        "feared_event": "leak",
        "attack_paths": [{"name": "supplier access"}],
    }
    assert workflow._record_strategic_scenarios(ctx, study, item)
    theft = StrategicScenario.objects.get(name="theft")
    assert theft.ro_to_couple == b and theft.focused_feared_event is None
    assert not theft.attack_paths.exists() and shared.strategic_scenario == other
