import uuid

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Asset
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User

from test_utils import EndpointTestsQueries

# Generic asset data for tests
ASSET_NAME = "Test Asset"
ASSET_DESCRIPTION = "Test Description"
ASSET_TYPE = ("PR", "Primary")
ASSET_TYPE2 = ("SP", "Support")
ASSET_PARENT_ASSETS = []


@pytest.mark.django_db
class TestAssetsUnauthenticated:
    """Perform tests on Assets API endpoint without authentication"""

    client = APIClient()

    def test_get_assets(self):
        """test to get assets from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_assets(self):
        """test to create assets with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_assets(self):
        """test to update assets with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + ASSET_NAME,
                "description": "new " + ASSET_DESCRIPTION,
            },
        )

    def test_delete_assets(self):
        """test to delete assets with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Assets",
            Asset,
            {"name": ASSET_NAME, "folder": Folder.objects.create(name="test")},
        )


@pytest.mark.django_db
class TestAssetsAuthenticated:
    """Perform tests on Assets API endpoint with authentication"""

    def test_get_assets(self, test):
        """test to get assets from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "type": ASSET_TYPE[0],
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
        )

    def test_create_assets(self, test):
        """test to create assets without a parent asset the API with authentication"""

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "type": ASSET_TYPE[0],
                "parent_assets": [],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_create_assets_with_parent(self, test):
        """test to create assets with a parent asset with the API with authentication"""

        root_asset = Asset.objects.create(
            name="root",
            description=ASSET_DESCRIPTION,
            type=ASSET_TYPE[0],
            folder=test.folder,
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "type": ASSET_TYPE2[0],
                "parent_assets": [str(root_asset.id)],
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE2[1],
                "parent_assets": [{"id": str(root_asset.id), "str": root_asset.name}],
            },
            base_count=1,
            item_search_field="name",
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_assets(self, test):
        """test to update assets with the API with authentication"""

        folder = Folder.objects.create(name="test2")

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Assets",
            Asset,
            {
                "name": ASSET_NAME,
                "description": ASSET_DESCRIPTION,
                "type": ASSET_TYPE[0],
                "folder": test.folder,
            },
            {
                "name": "new " + ASSET_NAME,
                "description": "new " + ASSET_DESCRIPTION,
                "type": ASSET_TYPE2[0],
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "type": ASSET_TYPE[1],
            },
            user_group=test.user_group,
        )

    def test_delete_assets(self, test):
        """test to delete assets with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Assets",
            Asset,
            {"name": ASSET_NAME, "folder": test.folder},
            user_group=test.user_group,
        )

    def test_get_type_choices(self, test):
        """test to get type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client, "Assets", "type", Asset.Type.choices
        )


# ---------------------------------------------------------------------------
# IAM-scoped visibility on /api/assets/.
#
# Locks down the queryset-level filter (`BaseModelViewSet.get_queryset`
# materialising `RoleAssignment._get_accessible_ids`) for a reader
# scoped to a single domain folder: an asset in a sibling folder must
# not appear in their list at all (and a fortiori not as a masked
# placeholder — masking is for related-field references, not list rows).
# ---------------------------------------------------------------------------


def _client_for(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _make_scoped_reader(folder):
    user = User.objects.create_user(f"reader-{uuid.uuid4().hex[:6]}@perf.test")
    role = Role.objects.get(name=RoleCodename.READER.value)
    ra = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    ra.perimeter_folders.add(folder)
    return user


@pytest.mark.django_db
class TestAssetListIAMScope:
    def test_scoped_reader_does_not_see_cross_folder_asset(self, authenticated_client):
        """Reader scoped to folder A must not see an asset in folder B
        in `/api/assets/` results — that asset is outside their scope at
        the queryset level (handled by `_get_accessible_ids`,
        before any post-filter masking)."""
        root = Folder.get_root_folder()
        folder_a = Folder.objects.create(
            name=f"perf-test-A-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        folder_b = Folder.objects.create(
            name=f"perf-test-B-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        asset_in_b = Asset.objects.create(
            folder=folder_b,
            name=f"asset-B-{uuid.uuid4().hex[:6]}",
            type=Asset.Type.PRIMARY,
        )

        client = _client_for(_make_scoped_reader(folder_a))
        r = client.get("/api/assets/")
        assert r.status_code == status.HTTP_200_OK, r.content
        body = r.json()
        results = body.get("results", body) if isinstance(body, dict) else body
        ids = {it["id"] for it in results}
        assert str(asset_in_b.id) not in ids, (
            f"scoped reader saw asset {asset_in_b.id} from another folder; "
            f"results: {ids}"
        )

    def _build_export_fixture(self):
        """Two folders × two asset types — A is in-scope, B is out-of-scope.
        Returns (client, assets) for the scoped reader of folder A."""
        root = Folder.get_root_folder()
        folder_a = Folder.objects.create(
            name=f"perf-test-A-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        folder_b = Folder.objects.create(
            name=f"perf-test-B-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        assets = {
            "a_pr": Asset.objects.create(
                folder=folder_a,
                name=f"asset-A-PR-{uuid.uuid4().hex[:6]}",
                type=Asset.Type.PRIMARY,
            ),
            "a_sp": Asset.objects.create(
                folder=folder_a,
                name=f"asset-A-SP-{uuid.uuid4().hex[:6]}",
                type=Asset.Type.SUPPORT,
            ),
            "b_pr": Asset.objects.create(
                folder=folder_b,
                name=f"asset-B-PR-{uuid.uuid4().hex[:6]}",
                type=Asset.Type.PRIMARY,
            ),
            "b_sp": Asset.objects.create(
                folder=folder_b,
                name=f"asset-B-SP-{uuid.uuid4().hex[:6]}",
                type=Asset.Type.SUPPORT,
            ),
        }
        return _client_for(_make_scoped_reader(folder_a)), assets

    def test_scoped_reader_export_csv_respects_scope_and_filter(self):
        """CSV export must honor both IAM scope and list filters: the
        scoped reader hitting /api/assets/export_csv/?type=PR sees only
        their folder's PR asset."""
        client, assets = self._build_export_fixture()
        r = client.get("/api/assets/export_csv/?type=PR")
        assert r.status_code == status.HTTP_200_OK, r.content
        assert r["Content-Type"] == "text/csv; charset=utf-8"
        content = r.content.decode("utf-8")

        assert assets["a_pr"].name in content, (
            f"scoped reader should see PR asset {assets['a_pr'].name} from their folder"
        )
        assert assets["a_sp"].name not in content, (
            f"scoped reader should not see SP asset {assets['a_sp'].name} (filtered by type)"
        )
        assert assets["b_pr"].name not in content, (
            f"scoped reader should not see PR asset {assets['b_pr'].name} from another folder"
        )
        assert assets["b_sp"].name not in content, (
            f"scoped reader should not see SP asset {assets['b_sp'].name} from another folder"
        )

    def test_scoped_reader_export_xlsx_respects_scope_and_filter(self):
        """XLSX export shares ExportMixin._get_export_queryset with CSV; this
        regression-guards against a future override that re-skips
        filter_queryset on the xlsx path."""
        import io
        from openpyxl import load_workbook

        client, assets = self._build_export_fixture()
        r = client.get("/api/assets/export_xlsx/?type=PR")
        assert r.status_code == status.HTTP_200_OK, r.content
        assert (
            r["Content-Type"]
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        wb = load_workbook(io.BytesIO(r.content), read_only=True)
        cells = {
            str(c.value)
            for ws in wb.worksheets
            for row in ws.iter_rows()
            for c in row
            if c.value is not None
        }

        assert assets["a_pr"].name in cells
        assert assets["a_sp"].name not in cells
        assert assets["b_pr"].name not in cells
        assert assets["b_sp"].name not in cells


@pytest.mark.django_db
class TestAssetFullEndpoint:
    """`/api/assets/full/` — bulk full-detail read. Must match the per-id
    detail payload (including the graph-derived objectives/capabilities/
    comparison fields computed once per page) and honor IAM like list."""

    @staticmethod
    def _bulk_map(client):
        r = client.get("/api/assets/full/?limit=1000")
        assert r.status_code == status.HTTP_200_OK, r.content
        body = r.json()
        results = body.get("results", body) if isinstance(body, dict) else body
        return {it["id"]: it for it in results}

    def test_full_matches_detail_payload(self, authenticated_client):
        """Bulk record == detail record for both a primary asset and a
        supporting asset that aggregates objectives from its primary parent
        (exercises the optimized comparison/capability reuse)."""
        root = Folder.get_root_folder()
        folder = Folder.objects.create(
            name=f"full-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        primary = Asset.objects.create(
            folder=folder, name="primary", type=Asset.Type.PRIMARY
        )
        support = Asset.objects.create(
            folder=folder, name="support", type=Asset.Type.SUPPORT
        )
        support.parent_assets.add(primary)

        bulk = self._bulk_map(authenticated_client)
        for asset in (primary, support):
            d = authenticated_client.get(f"/api/assets/{asset.id}/")
            assert d.status_code == status.HTTP_200_OK, d.content
            assert bulk[str(asset.id)] == d.json(), (
                f"bulk vs detail mismatch for asset {asset.id}"
            )

    def test_full_respects_iam_scope(self):
        """Reader scoped to folder A must not see an asset from folder B in
        /full/ results (queryset-level IAM scoping)."""
        root = Folder.get_root_folder()
        folder_a = Folder.objects.create(
            name=f"full-A-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        folder_b = Folder.objects.create(
            name=f"full-B-{uuid.uuid4().hex[:6]}",
            parent_folder=root,
            content_type=Folder.ContentType.DOMAIN,
        )
        asset_a = Asset.objects.create(
            folder=folder_a, name="a", type=Asset.Type.PRIMARY
        )
        asset_b = Asset.objects.create(
            folder=folder_b, name="b", type=Asset.Type.PRIMARY
        )

        bulk = self._bulk_map(_client_for(_make_scoped_reader(folder_a)))
        assert str(asset_a.id) in bulk
        assert str(asset_b.id) not in bulk, (
            f"scoped reader saw cross-folder asset {asset_b.id} in /full/"
        )


def _make_scoped_user(analyst_folder, reader_folder=None):
    user = User.objects.create_user(f"linker-{uuid.uuid4().hex[:6]}@perf.test")
    root = Folder.get_root_folder()
    for codename, folder in (
        (RoleCodename.ANALYST, analyst_folder),
        (RoleCodename.READER, reader_folder),
    ):
        if folder is None:
            continue
        ra = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=codename.value),
            folder=root,
            is_recursive=True,
        )
        ra.perimeter_folders.add(folder)
    return user


@pytest.mark.django_db
class TestCrossDomainAssetLinkPermissions:
    def _domain(self, label):
        return Folder.objects.create(
            name=f"link-{label}-{uuid.uuid4().hex[:6]}",
            parent_folder=Folder.get_root_folder(),
            content_type=Folder.ContentType.DOMAIN,
        )

    def setup_method(self):
        self.folder_a = self._domain("A")
        self.folder_b = self._domain("B")
        self.local = Asset.objects.create(
            folder=self.folder_a, name="local", type=Asset.Type.SUPPORT
        )
        self.sibling = Asset.objects.create(
            folder=self.folder_a, name="sibling", type=Asset.Type.PRIMARY
        )
        self.remote = Asset.objects.create(
            folder=self.folder_b, name="remote", type=Asset.Type.PRIMARY
        )

    def _patch(self, user, asset, payload):
        return _client_for(user).patch(
            f"/api/assets/{asset.id}/", payload, format="json"
        )

    def test_view_only_parent_cannot_be_linked(self):
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = self._patch(user, self.local, {"parent_assets": [str(self.remote.id)]})
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not self.local.parent_assets.exists()

    def test_changeable_parent_can_be_linked(self):
        user = _make_scoped_user(self.folder_a)
        extra = RoleAssignment.objects.create(
            user=user,
            role=Role.objects.get(name=RoleCodename.ANALYST.value),
            folder=Folder.get_root_folder(),
            is_recursive=True,
        )
        extra.perimeter_folders.add(self.folder_b)
        r = self._patch(user, self.local, {"parent_assets": [str(self.remote.id)]})
        assert r.status_code == status.HTTP_200_OK, r.content
        assert list(self.local.parent_assets.all()) == [self.remote]

    def test_view_only_asset_cannot_be_linked_as_support(self):
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = self._patch(user, self.sibling, {"support_assets": [str(self.remote.id)]})
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not self.remote.parent_assets.exists()

    def test_view_only_parent_cannot_be_unlinked(self):
        self.local.parent_assets.add(self.remote)
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = self._patch(user, self.local, {"parent_assets": []})
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert list(self.local.parent_assets.all()) == [self.remote]

    def test_invisible_parent_survives_a_save_that_omits_it(self):
        self.local.parent_assets.add(self.remote)
        user = _make_scoped_user(self.folder_a)
        r = self._patch(
            user,
            self.local,
            {"name": "renamed", "parent_assets": [str(self.sibling.id)]},
        )
        assert r.status_code == status.HTTP_200_OK, r.content
        self.local.refresh_from_db()
        assert self.local.name == "renamed"
        assert set(self.local.parent_assets.all()) == {self.remote, self.sibling}

    def test_invisible_support_asset_survives_a_save_that_omits_it(self):
        self.remote.parent_assets.add(self.sibling)
        user = _make_scoped_user(self.folder_a)
        r = self._patch(user, self.sibling, {"support_assets": [str(self.local.id)]})
        assert r.status_code == status.HTTP_200_OK, r.content
        assert set(self.sibling.child_assets.all()) == {self.remote, self.local}

    def test_existing_cross_domain_link_does_not_block_other_edits(self):
        self.local.parent_assets.add(self.remote)
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = self._patch(
            user,
            self.local,
            {
                "name": "renamed",
                "parent_assets": [str(self.remote.id), str(self.sibling.id)],
            },
        )
        assert r.status_code == status.HTTP_200_OK, r.content
        self.local.refresh_from_db()
        assert self.local.name == "renamed"
        assert set(self.local.parent_assets.all()) == {self.remote, self.sibling}

    def test_create_with_view_only_parent_is_refused(self):
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = _client_for(user).post(
            "/api/assets/",
            {
                "name": "new",
                "type": "SP",
                "folder": str(self.folder_a.id),
                "parent_assets": [str(self.remote.id)],
            },
            format="json",
        )
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not Asset.objects.filter(name="new", folder=self.folder_a).exists()

    def test_restored_invisible_parent_is_part_of_cycle_check(self):
        self.local.parent_assets.add(self.remote)
        self.remote.parent_assets.add(self.sibling)
        user = _make_scoped_user(self.folder_a)
        r = self._patch(
            user,
            self.local,
            {"parent_assets": [], "support_assets": [str(self.sibling.id)]},
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST, r.content
        assert not self.local.child_assets.exists()

    def _batch_create(self, user, folder, text):
        return _client_for(user).post(
            "/api/assets/batch-create/",
            {"assets_text": text, "folder": str(folder.id)},
            format="json",
        )

    def test_batch_create_refused_without_add_permission(self):
        user = _make_scoped_user(self.folder_a, self.folder_b)
        r = self._batch_create(user, self.folder_b, "PR:remote\n  SP:local-b")
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not Asset.objects.filter(name="local-b").exists()

    def test_batch_create_cannot_relink_assets_of_an_unseen_domain(self):
        other = Asset.objects.create(
            folder=self.folder_b, name="other", type=Asset.Type.SUPPORT
        )
        user = _make_scoped_user(self.folder_a)
        r = self._batch_create(user, self.folder_b, "PR:remote\n  SP:other")
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.content
        assert not other.parent_assets.exists()

    def test_batch_create_links_reused_assets(self):
        user = _make_scoped_user(self.folder_a)
        r = self._batch_create(user, self.folder_a, "PR:sibling\n  SP:local")
        assert r.status_code == status.HTTP_201_CREATED, r.content
        assert list(self.local.parent_assets.all()) == [self.sibling]

    def test_batch_create_refuses_a_cycle_between_reused_assets(self):
        self.local.parent_assets.add(self.sibling)
        user = _make_scoped_user(self.folder_a)
        r = self._batch_create(user, self.folder_a, "SP:local\n  PR:sibling")
        assert r.status_code == status.HTTP_201_CREATED, r.content
        assert r.json()["errors"], r.content
        assert not self.sibling.parent_assets.exists()
