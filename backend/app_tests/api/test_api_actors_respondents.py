import pytest
from rest_framework.test import APIClient

from core.models import Actor
from core.utils import UserGroupCodename
from iam.models import Folder, User, UserGroup


def _enclave_with_respondent(name: str, email: str) -> tuple[Folder, User]:
    enclave = Folder.objects.create(
        name=name,
        content_type=Folder.ContentType.ENCLAVE,
        parent_folder=Folder.get_root_folder(),
    )
    respondents = UserGroup.objects.create(
        name=UserGroupCodename.THIRD_PARTY_RESPONDENT.value,
        folder=enclave,
        builtin=True,
    )
    user = User.objects.create_user(email=email, is_third_party=True)
    user.user_groups.add(respondents)
    return enclave, user


def _actor_ids(client: APIClient, query: str = "") -> set[str]:
    response = client.get(f"/api/actors/?page_size=500{query}")
    assert response.status_code == 200, response.content
    return {actor["id"] for actor in response.json()["results"]}


@pytest.mark.django_db
def test_actors_offer_the_respondents_of_the_given_workspace_only(
    authenticated_client: APIClient,
) -> None:
    enclave, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    _, bob = _enclave_with_respondent("Vendor B", "bob@vendor-b.example")
    admin = Actor.objects.get(user__email="admin@tests.com")

    ids = _actor_ids(authenticated_client, f"&respondents_of={enclave.id}")

    assert str(admin.id) in ids
    assert str(alice.actor.id) in ids
    assert str(bob.actor.id) not in ids


@pytest.mark.django_db
def test_actors_list_only_the_respondents_when_asked(
    authenticated_client: APIClient,
) -> None:
    enclave, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    _enclave_with_respondent("Vendor B", "bob@vendor-b.example")

    ids = _actor_ids(
        authenticated_client, f"&respondents_of={enclave.id}&respondents_only=true"
    )

    assert ids == {str(alice.actor.id)}


@pytest.mark.django_db
def test_actors_still_hide_third_parties_without_a_workspace(
    authenticated_client: APIClient,
) -> None:
    _, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")

    assert str(alice.actor.id) not in _actor_ids(authenticated_client)
    assert str(alice.actor.id) not in _actor_ids(
        authenticated_client, "&respondents_of=not-a-uuid"
    )
