"""
`/iam/current-user/` sends each distinct codename set once (`permission_sets`) and maps
every folder to its set by index (`domain_permissions`). The indirection must be
lossless: resolving a folder's index gives back exactly its `get_permissions_per_folder`
codenames.
"""

import pytest
from knox.models import AuthToken
from rest_framework.test import APIClient

from core.apps import startup
from iam.models import Folder, RoleAssignment, User, UserGroup, UserGroupCodename


@pytest.fixture
def domain():
    startup(sender=None)
    domain = Folder.objects.create(
        name="Domain",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
        create_iam_groups=True,
    )
    Folder.create_default_ug_and_ra(domain)
    for i in range(3):
        Folder.objects.create(
            name=f"Subdomain {i}",
            parent_folder=domain,
            content_type=Folder.ContentType.DOMAIN,
        )
    return domain


def _current_user(user: User) -> dict:
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    response = client.get("/api/iam/current-user/")
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "group_name,on_domain",
    [("BI-UG-ADM", False), (str(UserGroupCodename.AUDITEE), True)],
)
def test_permission_sets_resolve_to_per_folder_codenames(domain, group_name, on_domain):
    group = UserGroup.objects.get(
        name=group_name, folder=domain if on_domain else Folder.get_root_folder()
    )
    user = User.objects.create_user(email=f"{group_name}@permission-sets.test")
    group.user_set.add(user)

    data = _current_user(user)
    permission_sets = data["permission_sets"]
    domain_permissions = data["domain_permissions"]
    expected = RoleAssignment.get_permissions_per_folder(user, is_recursive=True)

    assert domain_permissions.keys() == expected.keys()
    for folder_id, index in domain_permissions.items():
        assert set(permission_sets[index]) == expected[folder_id], folder_id

    # Sent once each, and none unreferenced.
    assert len({frozenset(s) for s in permission_sets}) == len(permission_sets)
    assert set(domain_permissions.values()) == set(range(len(permission_sets)))


@pytest.mark.django_db
def test_recursive_grant_shares_one_set_across_its_subtree(domain):
    user = User.objects.create_user(email="admin@permission-sets.test")
    UserGroup.objects.get(name="BI-UG-ADM").user_set.add(user)

    data = _current_user(user)

    # The admin role on root covers every folder, and already holds everything the
    # baseline default role adds on root: one set, however many folders it covers.
    assert len(data["permission_sets"]) == 1
    assert len(data["domain_permissions"]) == Folder.objects.count()
