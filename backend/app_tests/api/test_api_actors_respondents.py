import pytest
from rest_framework.test import APIClient

from core.models import Actor, ComplianceAssessment, Framework
from core.utils import UserGroupCodename
from iam.models import Folder, User, UserGroup
from tprm.models import Entity, EntityAssessment, Representative


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


def _vendor_audited_in(enclave: Folder, name: str) -> Entity:
    vendor = Entity.objects.create(name=name, folder=Folder.get_root_folder())
    audit = ComplianceAssessment.objects.create(
        name=f"{name} audit",
        framework=Framework.objects.create(name=f"{name} framework"),
        folder=enclave,
    )
    EntityAssessment.objects.create(
        name=f"{name} assessment",
        entity=vendor,
        folder=Folder.get_root_folder(),
        compliance_assessment=audit,
    )
    return vendor


def _preferred_respondents(client: APIClient, enclave: Folder) -> list[str]:
    response = client.get(
        f"/api/actors/?respondents_of={enclave.id}&respondents_only=true"
        "&preferred_only=true"
    )
    assert response.status_code == 200, response.content
    return [actor["id"] for actor in response.json()["results"]]


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


@pytest.mark.django_db
def test_actors_list_only_the_preferred_respondents_when_asked(
    authenticated_client: APIClient,
) -> None:
    enclave, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    carol = User.objects.create_user(
        email="carol@vendor-a.example", is_third_party=True
    )
    carol.user_groups.add(alice.user_groups.get())
    vendor = _vendor_audited_in(enclave, "Vendor A")
    Representative.objects.create(
        entity=vendor, email=alice.email, user=alice, is_preferred=True
    )
    Representative.objects.create(entity=vendor, email=carol.email, user=carol)

    assert _preferred_respondents(authenticated_client, enclave) == [
        str(alice.actor.id)
    ]


@pytest.mark.django_db
def test_actors_preferred_for_another_vendor_are_not_preferred_here(
    authenticated_client: APIClient,
) -> None:
    enclave, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    other_enclave, _ = _enclave_with_respondent("Vendor B", "bob@vendor-b.example")
    vendor_a = _vendor_audited_in(enclave, "Vendor A")
    vendor_b = _vendor_audited_in(other_enclave, "Vendor B")
    Representative.objects.create(entity=vendor_a, email=alice.email, user=alice)
    Representative.objects.create(
        entity=vendor_b, email="alice@vendor-b.example", user=alice, is_preferred=True
    )

    assert _preferred_respondents(authenticated_client, enclave) == []


@pytest.mark.django_db
def test_actors_list_a_respondent_once_whatever_their_preferred_records(
    authenticated_client: APIClient,
) -> None:
    enclave, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    vendor = _vendor_audited_in(enclave, "Vendor A")
    for email in [alice.email, "alice.new@vendor-a.example"]:
        Representative.objects.create(
            entity=vendor, email=email, user=alice, is_preferred=True
        )

    assert _preferred_respondents(authenticated_client, enclave) == [
        str(alice.actor.id)
    ]


@pytest.mark.django_db
def test_actors_list_no_preferred_respondent_without_a_workspace(
    authenticated_client: APIClient,
) -> None:
    _, alice = _enclave_with_respondent("Vendor A", "alice@vendor-a.example")
    vendor = Entity.objects.create(name="Vendor A", folder=Folder.get_root_folder())
    EntityAssessment.objects.create(
        name="Vendor A assessment", entity=vendor, folder=Folder.get_root_folder()
    )
    Representative.objects.create(
        entity=vendor, email=alice.email, user=alice, is_preferred=True
    )

    assert not _actor_ids(
        authenticated_client, "&include_third_parties=true&preferred_only=true"
    )
