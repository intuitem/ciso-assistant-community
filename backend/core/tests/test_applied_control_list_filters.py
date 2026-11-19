"""Applied control list filters: linked risk scenarios and excluded statuses."""

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


@pytest.fixture
def client(domain):
    admin = User.objects.create_superuser("admin@control-filters-tests.com")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(admin)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=admin)[1]}"
    )
    return client


@pytest.fixture
def scenarios(domain):
    matrix = RiskMatrix.objects.create(
        name="filters matrix",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    ra = RiskAssessment.objects.create(
        name="filters ra", folder=domain, risk_matrix=matrix
    )
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
