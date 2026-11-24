"""Applied control list filters: linked risk scenarios and excluded statuses."""

from uuid import uuid4

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import AppliedControl, RiskAssessment, RiskMatrix, RiskScenario
from core.startup import startup
from iam.models import Folder, User, UserGroup
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

pytestmark = pytest.mark.django_db


@pytest.fixture
def domain():
    startup(sender=None, **{})
    return Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="filters domain",
        content_type=Folder.ContentType.DOMAIN,
    )


def _token_client(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


@pytest.fixture
def client(domain):
    admin = User.objects.create_superuser("admin@control-filters-tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    return _token_client(admin)


def _risk_assessment(folder, name):
    matrix = RiskMatrix.objects.create(
        name=f"{name} matrix",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    return RiskAssessment.objects.create(name=name, folder=folder, risk_matrix=matrix)


@pytest.fixture
def scenarios(domain):
    ra = _risk_assessment(domain, "filters ra")
    return (
        RiskScenario.objects.create(risk_assessment=ra, name="S1"),
        RiskScenario.objects.create(risk_assessment=ra, name="S2"),
    )


def _control(domain, name, **kwargs):
    return AppliedControl.objects.create(name=name, folder=domain, **kwargs)


def _names(client, query):
    response = client.get(f"/api/applied-controls/?{query}")
    assert response.status_code == 200, response.content
    return {row["name"] for row in response.json()["results"]}


def test_linked_risk_scenarios_matches_existing_and_additional(
    client, domain, scenarios
):
    s1, s2 = scenarios
    existing = _control(domain, "existing")
    additional = _control(domain, "additional")
    other = _control(domain, "other scenario")
    _control(domain, "unlinked")
    s1.existing_applied_controls.add(existing)
    s1.applied_controls.add(additional)
    s2.applied_controls.add(other)

    assert _names(client, f"linked_risk_scenarios={s1.id}") == {
        "existing",
        "additional",
    }
    assert _names(
        client, f"linked_risk_scenarios={s1.id}&linked_risk_scenarios={s2.id}"
    ) == {"existing", "additional", "other scenario"}


def test_linked_risk_scenarios_lists_a_control_once(client, domain, scenarios):
    s1, s2 = scenarios
    both = _control(domain, "both links")
    s1.existing_applied_controls.add(both)
    s1.applied_controls.add(both)
    s2.applied_controls.add(both)

    response = client.get(
        f"/api/applied-controls/?linked_risk_scenarios={s1.id}"
        f"&linked_risk_scenarios={s2.id}"
    )
    assert response.json()["count"] == 1


def test_exclude_status_drops_only_that_status(client, domain):
    _control(domain, "active", status=AppliedControl.Status.ACTIVE)
    _control(domain, "in progress", status=AppliedControl.Status.IN_PROGRESS)
    _control(domain, "undefined")

    assert _names(client, "exclude_status=active") == {"in progress", "undefined"}


def test_impact_effort_honors_exclude_status(client, domain):
    _control(
        domain,
        "active",
        status=AppliedControl.Status.ACTIVE,
        control_impact=5,
        effort="XS",
    )
    _control(
        domain,
        "to do",
        status=AppliedControl.Status.TO_DO,
        control_impact=5,
        effort="XS",
    )

    def cell(query=""):
        # Impact 5 is the first row, effort XS the first column.
        response = client.get(f"/api/applied-controls/impact_effort/{query}")
        assert response.status_code == 200, response.content
        return {item["name"] for item in response.json()[0][0]}

    assert cell() == {"active", "to do"}
    assert cell("?exclude_status=active") == {"to do"}


@pytest.fixture
def hidden_link(domain):
    """A reader of one domain, and a control there linked both ways to a
    scenario they can view and to one in a domain they cannot."""

    def iam_domain(name):
        folder = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name=name,
            content_type=Folder.ContentType.DOMAIN,
            create_iam_groups=True,
        )
        Folder.create_default_ug_and_ra(folder)
        return folder

    visible_domain = iam_domain("visible domain")
    hidden_domain = iam_domain("hidden domain")
    seen = RiskScenario.objects.create(
        risk_assessment=_risk_assessment(visible_domain, "seen ra"), name="seen"
    )
    unseen = RiskScenario.objects.create(
        risk_assessment=_risk_assessment(hidden_domain, "unseen ra"), name="unseen"
    )
    control = _control(visible_domain, "shared control")
    for scenario in (seen, unseen):
        scenario.applied_controls.add(control)
        scenario.existing_applied_controls.add(control)

    reader = User.objects.create_user("reader@control-filters-tests.com")
    UserGroup.objects.get(name="BI-UG-AUD", folder=visible_domain).user_set.add(reader)
    return _token_client(reader), seen, unseen


@pytest.mark.parametrize(
    "param, attribute",
    [
        ("linked_risk_scenarios", "id"),
        ("risk_scenarios", "id"),
        ("risk_scenarios_e", "id"),
        ("risk_assessments", "risk_assessment_id"),
    ],
)
def test_filters_reject_objects_the_user_cannot_view(hidden_link, param, attribute):
    reader_client, seen, unseen = hidden_link

    assert _names(reader_client, f"{param}={getattr(seen, attribute)}") == {
        "shared control"
    }
    # A hidden object is refused exactly like one that does not exist.
    hidden = reader_client.get(
        f"/api/applied-controls/?{param}={getattr(unseen, attribute)}"
    )
    unknown = reader_client.get(f"/api/applied-controls/?{param}={uuid4()}")
    assert hidden.status_code == unknown.status_code == 400
    assert set(hidden.json()) == set(unknown.json()) == {param}
