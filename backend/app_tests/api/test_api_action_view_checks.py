"""Actions that build their own response give no more than the list and detail
endpoints do: no object the caller cannot view, no actor the caller cannot view,
and the linked objects the caller cannot view masked."""

import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from rest_framework import status

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    Finding,
    FindingsAssessment,
    Framework,
    Perimeter,
    RiskAcceptance,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    TaskTemplate,
)
from iam.models import Folder, User
from privacy.models import Processing, RightRequest
from test_api_requirements_list_masking import _analyst, _domain
from test_fixtures import RISK_MATRIX_JSON_DEFINITION


@pytest.fixture
def world(db):
    """An analyst working in one domain, a domain they cannot see and a user they
    cannot view. Whatever the analyst must not learn of is named "concealed"."""
    mine, hidden = _domain("mine"), _domain("hidden")
    user, client = _analyst(mine)
    return SimpleNamespace(
        mine=mine,
        hidden=hidden,
        user=user,
        client=client,
        stranger=User.objects.create_user("concealed@test.com"),
        perimeter=Perimeter.objects.create(name="perimeter", folder=mine),
        soon=date.today() + timedelta(days=5),
    )


def _body(response):
    assert response.status_code == status.HTTP_200_OK, response.content
    assert "concealed" not in response.content.decode()
    return response.json()


def _audit(name, folder, perimeter):
    framework = Framework.objects.create(
        name="fw",
        folder=Folder.get_root_folder(),
        urn=f"urn:test:risk:framework:{uuid.uuid4().hex[:6]}",
    )
    return ComplianceAssessment.objects.create(
        name=name, framework=framework, folder=folder, perimeter=perimeter
    )


def _risk_assessment(name, folder, perimeter):
    return RiskAssessment.objects.create(
        name=name,
        folder=folder,
        perimeter=perimeter,
        risk_matrix=RiskMatrix.objects.create(
            name="matrix", folder=folder, json_definition=RISK_MATRIX_JSON_DEFINITION
        ),
    )


def _concealed(model, world):
    return model.objects.create(name=f"concealed {model.__name__}", folder=world.hidden)


@pytest.mark.django_db
def test_perimeter_quality_check_leaves_out_assessments_the_user_cannot_view(world):
    audit = _audit("audit", world.mine, world.perimeter)
    audit.assets.set([_concealed(Asset, world)])
    _audit("concealed audit", world.hidden, world.perimeter)
    risk_assessment = _risk_assessment("risk assessment", world.mine, world.perimeter)
    _risk_assessment("concealed risk assessment", world.hidden, world.perimeter)

    every = _body(world.client.get("/api/perimeters/quality_check/"))["results"]
    one = _body(
        world.client.get(f"/api/perimeters/{world.perimeter.id}/quality_check/")
    )

    for entry in (every[str(world.perimeter.id)], one):
        audits = entry["compliance_assessments"]["objects"]
        assert list(audits) == [str(audit.id)]
        assert audits[str(audit.id)]["object"]["assets"] == [{}]
        assert list(entry["risk_assessments"]["objects"]) == [str(risk_assessment.id)]


@pytest.mark.django_db
def test_my_assignments_leaves_out_objects_the_user_cannot_view(world):
    me = world.user.actor
    assigned = {}
    for label, folder in (("", world.mine), ("concealed ", world.hidden)):
        control = AppliedControl.objects.create(name=f"{label}control", folder=folder)
        control.owner.set([me])
        audit = _audit(f"{label}audit", folder, world.perimeter)
        audit.authors.set([me])
        risk_assessment = _risk_assessment(f"{label}ra", folder, world.perimeter)
        risk_assessment.reviewers.set([me])
        scenario = RiskScenario.objects.create(
            name=f"{label}scenario", risk_assessment=risk_assessment
        )
        scenario.owner.set([me])
        assigned[label] = (control, audit, risk_assessment, scenario)
    control, audit, risk_assessment, scenario = assigned[""]
    control.assets.set([_concealed(Asset, world)])

    data = _body(world.client.get("/api/folders/my_assignments/"))

    for key, expected in (
        ("controls", control),
        ("audits", audit),
        ("risk_assessments", risk_assessment),
        ("risk_scenarios", scenario),
    ):
        assert [item["id"] for item in data[key]] == [str(expected.id)]
    assert data["controls"][0]["assets"] == [{}]


def _finding(world):
    return Finding.objects.create(
        name="finding",
        findings_assessment=FindingsAssessment.objects.create(
            name="follow-up", folder=world.hidden, perimeter=world.perimeter
        ),
    )


OWNER_LISTS = {
    "/api/applied-controls/owner/": lambda world: (
        _concealed(AppliedControl, world).owner
    ),
    "/api/evidences/owner/": lambda world: _concealed(Evidence, world).owner,
    "/api/findings/owner/": lambda world: _finding(world).owner,
    "/api/task-templates/assigned_to/": lambda world: (
        _concealed(TaskTemplate, world).assigned_to
    ),
    "/api/privacy/processings/assigned_to/": lambda world: (
        _concealed(Processing, world).assigned_to
    ),
    "/api/privacy/right-requests/owner/": lambda world: (
        RightRequest.objects.create(
            name="request", folder=world.hidden, requested_on=date.today()
        ).owner
    ),
}


@pytest.mark.django_db
@pytest.mark.parametrize("url", OWNER_LISTS)
def test_owner_list_names_only_the_actors_the_user_can_view(
    world, authenticated_client, url
):
    OWNER_LISTS[url](world).set([world.stranger.actor])

    assert _body(world.client.get(url)) == []
    (actor,) = authenticated_client.get(url).json()
    assert actor["id"] == str(world.stranger.actor.id)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/api/applied-controls/todo/",
        "/api/applied-controls/to_review/",
        "/api/requirement-assessments/todo/",
        "/api/requirement-assessments/to_review/",
    ],
)
def test_applied_controls_to_do_and_to_review_mask_hidden_links(world, url):
    dates = {"eta": world.soon, "expiry_date": world.soon}
    control = AppliedControl.objects.create(name="control", folder=world.mine, **dates)
    control.evidences.set([_concealed(Evidence, world)])
    control.owner.set([world.stranger.actor])
    AppliedControl.objects.create(
        name="concealed control", folder=world.hidden, **dates
    )

    (entry,) = _body(world.client.get(url))["results"]

    assert entry["id"] == str(control.id)
    assert entry["evidences"] == [{}]
    assert entry["owner"] == [{}]


@pytest.mark.django_db
def test_risk_acceptances_to_review_mask_hidden_scenarios(world):
    scenario, concealed = (
        RiskScenario.objects.create(
            name=f"{label}scenario",
            risk_assessment=_risk_assessment(f"{label}ra", folder, world.perimeter),
        )
        for label, folder in (("", world.mine), ("concealed ", world.hidden))
    )
    acceptance = RiskAcceptance.objects.create(
        name="acceptance",
        folder=world.mine,
        approver=world.user,
        expiry_date=world.soon,
        state="submitted",
    )
    acceptance.risk_scenarios.set([scenario, concealed])

    (entry,) = _body(world.client.get("/api/risk-acceptances/to_review/"))["results"]

    assert {} in entry["risk_scenarios"]
    assert [item["id"] for item in entry["risk_scenarios"] if item] == [
        str(scenario.id)
    ]


@pytest.mark.django_db
def test_task_calendar_and_yearly_review_mask_hidden_links(world):
    today = date.today()
    task = TaskTemplate.objects.create(
        name="task",
        folder=world.mine,
        task_date=today,
        is_recurrent=True,
        schedule={"interval": 1, "frequency": "YEARLY"},
    )
    task.assets.set([_concealed(Asset, world)])
    task.applied_controls.set([_concealed(AppliedControl, world)])

    start, end = today - timedelta(days=3), today + timedelta(days=20)
    (occurrence,) = _body(
        world.client.get(f"/api/task-templates/calendar/{start}/{end}/")
    )
    (folder,) = _body(world.client.get("/api/task-templates/yearly_review/"))["folders"]
    (row,) = folder["tasks"]

    for entry in (occurrence, row):
        assert entry["assets"] == [{}]
        assert entry["applied_controls"] == [{}]


@pytest.mark.django_db
def test_composer_data_masks_hidden_links(world):
    risk_assessment = _risk_assessment("ra", world.mine, world.perimeter)
    scenario = RiskScenario.objects.create(
        name="scenario", risk_assessment=risk_assessment
    )
    scenario.assets.set([_concealed(Asset, world)])
    scenario.owner.set([world.stranger.actor])

    result = _body(
        world.client.get(f"/api/composer_data/?risk_assessment={risk_assessment.id}")
    )["result"]

    (untreated,) = result["riskscenarios"]["untreated"]
    assert untreated["id"] == str(scenario.id)
    assert untreated["assets"] == [{}]
    assert untreated["owner"] == [{}]
