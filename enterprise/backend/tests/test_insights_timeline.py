"""Insights timeline: applied controls carry the risk scenarios they are linked to."""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.models import AppliedControl, RiskAssessment, RiskMatrix, RiskScenario
from iam.models import Folder, User, UserGroup
from test_fixtures import RISK_MATRIX_JSON_DEFINITION

pytestmark = pytest.mark.django_db


def _client(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


def _scenario(folder, name):
    matrix = RiskMatrix.objects.create(
        name=f"{name} matrix",
        folder=Folder.get_root_folder(),
        json_definition=RISK_MATRIX_JSON_DEFINITION,
    )
    ra = RiskAssessment.objects.create(
        name=f"{name} ra", folder=folder, risk_matrix=matrix
    )
    return RiskScenario.objects.create(risk_assessment=ra, name=name)


def _control_scenarios(client):
    response = client.get("/api/insights-timeline/")
    assert response.status_code == 200, response.content
    return {
        entry["name"]: set(entry["risk_scenarios"])
        for entry in response.json()
        if entry["model"] == "applied_controls"
    }


def test_controls_carry_existing_and_additional_scenarios(admin_client, domain):
    first = _scenario(domain, "first")
    second = _scenario(domain, "second")
    control = AppliedControl.objects.create(name="linked", folder=domain)
    AppliedControl.objects.create(name="unlinked", folder=domain)
    first.existing_applied_controls.add(control)
    first.applied_controls.add(control)
    second.applied_controls.add(control)

    scenarios = _control_scenarios(admin_client)
    assert scenarios["linked"] == {str(first.id), str(second.id)}
    assert scenarios["unlinked"] == set()


def test_scenarios_the_user_cannot_view_are_left_out(domain):
    other = Folder.objects.create(
        parent_folder=Folder.get_root_folder(),
        name="EE other domain",
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(other)
    visible = _scenario(domain, "visible")
    hidden = _scenario(other, "hidden")
    control = AppliedControl.objects.create(name="shared", folder=domain)
    visible.applied_controls.add(control)
    hidden.existing_applied_controls.add(control)

    reader = User.objects.create_user("timeline.reader@ee-tests.com")
    UserGroup.objects.get(name="BI-UG-AUD", folder=domain).user_set.add(reader)

    assert _control_scenarios(_client(reader)) == {"shared": {str(visible.id)}}
