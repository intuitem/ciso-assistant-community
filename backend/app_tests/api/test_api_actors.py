import pytest
from django.urls import reverse
from rest_framework import status

from core.models import Team
from iam.models import User


def _ids(response):
    assert response.status_code == status.HTTP_200_OK
    return {row["id"] for row in response.json()["results"]}


@pytest.fixture
def actors():
    active = User.objects.create_user(email="active@tests.com")
    inactive = User.objects.create_user(email="inactive@tests.com", is_active=False)
    # A team led by a deactivated user is still an assignable team.
    team = Team.objects.create(name="Team", leader=inactive)
    return {
        "active": str(active.actor.id),
        "inactive": str(inactive.actor.id),
        "team": str(team.actor.id),
    }


@pytest.mark.django_db
class TestDeactivatedActors:
    @pytest.mark.parametrize("route", ["actors-list", "actors-autocomplete"])
    def test_hidden_from_browsing(self, authenticated_client, actors, route):
        ids = _ids(authenticated_client.get(reverse(route)))

        assert actors["inactive"] not in ids
        assert actors["active"] in ids
        assert actors["team"] in ids

    @pytest.mark.parametrize("route", ["actors-list", "actors-autocomplete"])
    def test_include_inactive_lists_them(self, authenticated_client, actors, route):
        ids = _ids(
            authenticated_client.get(reverse(route), {"include_inactive": "true"})
        )

        assert {actors["inactive"], actors["active"], actors["team"]} <= ids

    @pytest.mark.parametrize("route", ["actors-list", "actors-autocomplete"])
    def test_selected_value_hydration(self, authenticated_client, actors, route):
        """Pickers resolve the value an object already holds by id; a deactivated
        owner must come back, or the next save would clear it."""
        ids = _ids(
            authenticated_client.get(
                reverse(route),
                {
                    "id": f"{actors['inactive']},{actors['active']}",
                    "include_inactive": "true",
                },
            )
        )

        assert ids == {actors["inactive"], actors["active"]}

    def test_search_with_include_inactive(self, authenticated_client, actors):
        """The MCP server resolves an owner named by email or name this way."""
        url = reverse("actors-list")

        assert _ids(authenticated_client.get(url, {"search": "inactive@"})) == set()
        assert _ids(
            authenticated_client.get(
                url, {"search": "inactive@", "include_inactive": "true"}
            )
        ) == {actors["inactive"]}

    def test_retrieve_by_id_unaffected(self, authenticated_client, actors):
        response = authenticated_client.get(
            reverse("actors-detail", args=[actors["inactive"]])
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == actors["inactive"]
