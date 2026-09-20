"""`GET /users/{id}/teams/` — the "which teams am I in, and as what" endpoint behind
the My profile page.

Membership is three separate relations, and which one matched is the point: it is why
the user is reached when the team is addressed (Team.get_emails).
"""

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import Team
from core.views import UserViewSet
from iam.models import Folder, User

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


def call(actor, target):
    view = UserViewSet.as_view({"get": "teams"})
    request = factory.get(f"/api/users/{target.id}/teams/")
    force_authenticate(request, user=actor)
    response = view(request, pk=str(target.id))
    response.render()
    return response


@pytest.fixture
def folder(db):
    return Folder.objects.create(
        name="Teams domain", content_type=Folder.ContentType.DOMAIN
    )


@pytest.fixture
def user(db):
    return User.objects.create(email="member@test.local")


def test_each_relation_reports_its_own_role(folder, user):
    led = Team.objects.create(name="SRE", folder=folder, leader=user)
    deputised = Team.objects.create(name="OPS", folder=folder)
    deputised.deputies.add(user)
    joined = Team.objects.create(name="SEC", folder=folder)
    joined.members.add(user)
    Team.objects.create(name="Unrelated", folder=folder)

    rows = call(user, user).data

    assert {r["str"]: r["role"] for r in rows} == {
        str(led): "leader",
        str(deputised): "deputy",
        str(joined): "member",
    }


def test_leader_wins_when_the_user_is_also_a_member(folder, user):
    """Naming the strongest relation, not an arbitrary one."""
    team = Team.objects.create(name="SRE", folder=folder, leader=user)
    team.members.add(user)

    rows = call(user, user).data

    assert len(rows) == 1, "one row per team, not one per relation"
    assert rows[0]["role"] == "leader"


def test_a_user_with_no_team_gets_an_empty_list(user):
    assert call(user, user).data == []


def test_reading_someone_else_is_exactly_as_permitted_as_reading_their_record(
    folder, user
):
    """The action adds no surface of its own: `get_object()` is the same gate the
    plain user detail endpoint uses."""
    other = User.objects.create(email="stranger@test.local")
    Team.objects.create(name="SRE", folder=folder, leader=other)

    detail = UserViewSet.as_view({"get": "retrieve"})
    request = factory.get(f"/api/users/{other.id}/")
    force_authenticate(request, user=user)
    baseline = detail(request, pk=str(other.id))

    assert call(user, other).status_code == baseline.status_code
