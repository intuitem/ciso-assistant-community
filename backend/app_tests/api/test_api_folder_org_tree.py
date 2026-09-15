"""Tests for /api/folders/org_tree/.

The endpoint had three N+1s — an ancestor walk, a per-node children query, and a
per-folder permission check — which together cost ~1250 queries on a 150-folder
instance. They are gone; the query-count test below is what keeps them gone, since
the shape tests would all still pass with the slow implementation.
"""

import pytest
from rest_framework import status

from core.models import Perimeter
from iam.models import Folder

ENDPOINT = "/api/folders/org_tree/"


def _tree():
    """root -> a -> a1 -> a2, root -> b (+ one perimeter under a)"""
    root = Folder.get_root_folder()
    a = Folder.objects.create(name="tree A", parent_folder=root)
    a1 = Folder.objects.create(name="tree A1", parent_folder=a)
    a2 = Folder.objects.create(name="tree A2", parent_folder=a1)
    b = Folder.objects.create(name="tree B", parent_folder=root)
    Perimeter.objects.create(name="tree perimeter", folder=a)
    return root, a, a1, a2, b


def _find(node, name):
    if node.get("name") == name:
        return node
    for child in node.get("children", []):
        found = _find(child, name)
        if found:
            return found
    return None


@pytest.mark.django_db
class TestFolderOrgTree:
    def test_returns_the_hierarchy_nested(self, authenticated_client):
        _tree()
        response = authenticated_client.get(f"{ENDPOINT}?include_perimeters=false")
        assert response.status_code == status.HTTP_200_OK
        body = response.json()

        a = _find(body, "tree A")
        assert a is not None, "a top-level domain must appear under the root"
        a1 = _find(a, "tree A1")
        assert a1 is not None, "nesting must be preserved"
        assert _find(a1, "tree A2") is not None, "nesting must go deeper than one level"
        # A sibling branch must not be swallowed into another one.
        assert _find(a, "tree B") is None
        assert _find(body, "tree B") is not None

    def test_perimeters_are_included_only_when_asked(self, authenticated_client):
        _tree()
        without = authenticated_client.get(
            f"{ENDPOINT}?include_perimeters=false"
        ).json()
        assert _find(without, "tree perimeter") is None

        with_them = authenticated_client.get(
            f"{ENDPOINT}?include_perimeters=true"
        ).json()
        perimeter = _find(with_them, "tree perimeter")
        assert perimeter is not None
        assert perimeter["symbol"] == "circle"

    def test_enclaves_are_excluded_by_default(self, authenticated_client):
        root, a, _, _, _ = _tree()
        Folder.objects.create(
            name="tree enclave",
            parent_folder=a,
            content_type=Folder.ContentType.ENCLAVE,
        )

        default = authenticated_client.get(ENDPOINT).json()
        assert _find(default, "tree enclave") is None

        included = authenticated_client.get(f"{ENDPOINT}?include_enclaves=true").json()
        enclave = _find(included, "tree enclave")
        assert enclave is not None
        assert enclave["symbol"] == "triangle"

    def test_write_perm_annotates_writable(self, authenticated_client):
        _tree()
        # An admin holds change_folder everywhere, so every node is writable...
        allowed = authenticated_client.get(
            f"{ENDPOINT}?write_perm=change_folder"
        ).json()
        assert _find(allowed, "tree A")["writable"] is True

        # ...and an unresolvable codename must deny rather than fail open.
        denied = authenticated_client.get(
            f"{ENDPOINT}?write_perm=not_a_real_perm"
        ).json()
        assert _find(denied, "tree A")["writable"] is False

        # Without the param the flag is not an assertion about permission at all.
        plain = authenticated_client.get(ENDPOINT).json()
        assert _find(plain, "tree A")["writable"] is True

    def test_query_count_does_not_grow_with_the_tree(
        self, authenticated_client, django_assert_max_num_queries
    ):
        """The guard against the N+1s coming back.

        Deliberately built wide *and* deep: under the old implementation this shape
        cost one query per folder for children, one per folder per level for
        ancestors, and one per folder for the permission check.
        """
        root = Folder.get_root_folder()
        parent = root
        for depth in range(6):
            parent = Folder.objects.create(name=f"deep {depth}", parent_folder=parent)
            for i in range(5):
                Folder.objects.create(name=f"wide {depth}-{i}", parent_folder=parent)

        with django_assert_max_num_queries(20):
            response = authenticated_client.get(
                f"{ENDPOINT}?include_perimeters=true&write_perm=change_folder"
            )
        assert response.status_code == status.HTTP_200_OK
        assert _find(response.json(), "deep 5") is not None
