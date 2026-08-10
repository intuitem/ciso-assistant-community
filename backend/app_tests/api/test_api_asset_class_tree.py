import pytest
from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Asset, AssetClass
from iam.models import Folder, Role, RoleAssignment, User, UserGroup


@pytest.fixture
def class_tree_assets():
    """Machines > Servers, with assets on both levels plus one unclassified."""
    root_folder = Folder.get_root_folder()
    domain = Folder.objects.create(
        name="ACT Domain",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )
    machines = AssetClass.objects.create(name="ACTMachines")
    servers = AssetClass.objects.create(name="ACTServers", parent=machines)

    Asset.objects.create(name="ACT direct", folder=domain, asset_class=machines)
    Asset.objects.create(name="ACT leaf 1", folder=domain, asset_class=servers)
    Asset.objects.create(name="ACT leaf 2", folder=domain, asset_class=servers)
    Asset.objects.create(name="ACT unclassified", folder=domain)
    return {"domain": domain, "machines": machines, "servers": servers}


def _find(nodes, name):
    for node in nodes:
        if node["name"] == name:
            return node
        found = _find(node["children"], name)
        if found:
            return found
    return None


@pytest.mark.django_db
class TestAssetClassTreeCounts:
    def test_counts_roll_up_through_the_tree(
        self, authenticated_client, class_tree_assets
    ):
        response = authenticated_client.get(reverse("assets-class-tree"))

        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        machines = _find(body["tree"], "ACTMachines")
        servers = _find(body["tree"], "ACTServers")
        assert machines["direct_count"] == 1
        assert machines["total_count"] == 3
        assert servers["direct_count"] == 2
        assert servers["total_count"] == 2

    def test_unclassified_assets_are_reported_separately(
        self, authenticated_client, class_tree_assets
    ):
        body = authenticated_client.get(reverse("assets-class-tree")).json()

        assert body["unclassified_count"] >= 1
        assert body["total_count"] == Asset.objects.count()

    def test_totals_are_not_broken_by_queryset_ordering(
        self, authenticated_client, class_tree_assets
    ):
        """The viewset orders by folder__name/name, and a queryset's ordering
        fields land in the GROUP BY, which would make this one row per asset."""
        body = authenticated_client.get(reverse("assets-class-tree")).json()

        assert _find(body["tree"], "ACTServers")["direct_count"] == 2

    def test_counts_honour_active_filters(
        self, authenticated_client, class_tree_assets
    ):
        other = Folder.objects.create(
            name="ACT Other",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        Asset.objects.create(
            name="ACT elsewhere", folder=other, asset_class=class_tree_assets["servers"]
        )

        body = authenticated_client.get(
            reverse("assets-class-tree"), {"folder": str(other.id)}
        ).json()

        assert _find(body["tree"], "ACTServers")["direct_count"] == 1
        assert body["total_count"] == 1


@pytest.mark.django_db
class TestAssetClassTreeIAM:
    def _scoped_client(self, email, folder):
        user = User.objects.create_user(email)
        group = UserGroup.objects.create(name=f"act-{email}", folder=folder)
        group.user_set.add(user)
        RoleAssignment.objects.create(
            user_group=group,
            role=Role.objects.get(name="BI-RL-ANA"),
            folder=folder,
            is_recursive=True,
        ).perimeter_folders.add(folder)
        client = APIClient()
        _, token = AuthToken.objects.create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return client

    def test_counts_are_limited_to_accessible_assets(self, class_tree_assets):
        """A user scoped to another domain must not learn how many assets exist
        elsewhere, not even through the counts."""
        other = Folder.objects.create(
            name="ACT Foreign",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )
        client = self._scoped_client("act-scoped@test.com", other)

        body = client.get(reverse("assets-class-tree")).json()

        assert body["total_count"] == 0
        assert body["unclassified_count"] == 0
        assert _find(body["tree"], "ACTServers")["total_count"] == 0

    def test_user_sees_assets_in_their_own_domain(self, class_tree_assets):
        client = self._scoped_client(
            "act-insider@test.com", class_tree_assets["domain"]
        )

        body = client.get(reverse("assets-class-tree")).json()

        assert body["total_count"] == 4
        assert _find(body["tree"], "ACTServers")["direct_count"] == 2
