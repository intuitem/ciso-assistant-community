import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from core.models import AppliedControl, Perimeter, Policy, RiskAssessment, RiskMatrix
from iam.models import Folder, User, UserGroup


@pytest.fixture
def app_ready(db):
    startup(sender=None)
    return Folder.get_root_folder()


def _client(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def victim_folder(app_ready):
    return Folder.objects.create(
        name="Victim", parent_folder=app_ready, content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def norole_client(app_ready):
    user = User.objects.create_user("norole@charts.test", is_published=True)
    user.folder = app_ready
    user.save()
    return _client(user)


@pytest.fixture
def admin_client(app_ready):
    user = User.objects.create_user("admin@charts.test", is_published=True)
    group = UserGroup.objects.get(name="BI-UG-ADM", folder=app_ready)
    user.folder = group.folder
    user.save()
    group.user_set.add(user)
    return _client(user)


@pytest.fixture
def victim_control(victim_folder):
    return AppliedControl.objects.create(
        name="CANARY-CONTROL", folder=victim_folder, status="to_do", priority=1
    )


@pytest.fixture
def victim_policy(victim_folder):
    return Policy.objects.create(
        name="CANARY-POLICY", folder=victim_folder, status="to_do", priority=1
    )


@pytest.fixture
def victim_risk_assessment(victim_folder, app_ready):
    perimeter = Perimeter.objects.create(name="CANARY-PERIMETER", folder=victim_folder)
    return RiskAssessment.objects.create(
        name="CANARY-ASSESSMENT",
        perimeter=perimeter,
        risk_matrix=RiskMatrix.objects.create(
            name="m", folder=app_ready, json_definition="{}"
        ),
    )


def test_priority_chart_data_hides_other_folders(norole_client, victim_control):
    resp = norole_client.get("/api/applied-controls/priority_chart_data/")
    assert resp.status_code == 200
    assert "CANARY-CONTROL" not in resp.content.decode()
    assert str(victim_control.id) not in resp.content.decode()


def test_policy_priority_chart_data_hides_other_folders(norole_client, victim_policy):
    resp = norole_client.get("/api/policies/priority_chart_data/")
    assert resp.status_code == 200
    assert "CANARY-POLICY" not in resp.content.decode()


def test_priority_chart_data_shows_own_folder(admin_client, victim_control):
    resp = admin_client.get("/api/applied-controls/priority_chart_data/")
    assert resp.status_code == 200
    assert "CANARY-CONTROL" in resp.content.decode()


def test_composer_data_denies_unviewable_assessment(
    norole_client, victim_risk_assessment
):
    resp = norole_client.get(
        f"/api/composer_data/?risk_assessment={victim_risk_assessment.id}"
    )
    assert resp.status_code == 403
    assert "CANARY-ASSESSMENT" not in resp.content.decode()


def test_composer_data_allows_viewable_assessment(admin_client, victim_risk_assessment):
    resp = admin_client.get(
        f"/api/composer_data/?risk_assessment={victim_risk_assessment.id}"
    )
    assert resp.status_code == 200
    assert "CANARY-ASSESSMENT" in resp.content.decode()
