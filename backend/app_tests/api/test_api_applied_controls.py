import uuid

import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Asset, ReferenceControl, AppliedControl
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User

from test_utils import EndpointTestsQueries

# Generic applied control data for tests
APPLIED_CONTROL_NAME = "Test Applied Control"
APPLIED_CONTROL_DESCRIPTION = "Test Description"
APPLIED_CONTROL_CATEGORY = ("technical", "Technical")
APPLIED_CONTROL_CATEGORY2 = ("process", "Process")
APPLIED_CONTROL_STATUS = AppliedControl.Status.IN_PROGRESS
APPLIED_CONTROL_STATUS2 = AppliedControl.Status.ACTIVE
APPLIED_CONTROL_EFFORT = ("L", "Large")
APPLIED_CONTROL_EFFORT2 = ("M", "Medium")
APPLIED_CONTROL_LINK = "https://example.com"
APPLIED_CONTROL_ETA = "2024-01-01"
APPLIED_CONTROL_COST = {
    "currency": "€",
    "amortization_period": 1,
    "build": {"fixed_cost": 24.42, "people_days": 0},
    "run": {"fixed_cost": 0, "people_days": 0},
}
APPLIED_CONTROL_COST2 = {
    "currency": "$",
    "amortization_period": 2,
    "build": {"fixed_cost": 25.43, "people_days": 2},
    "run": {"fixed_cost": 10.50, "people_days": 1},
}


@pytest.mark.django_db
class TestAppliedControlsUnauthenticated:
    """Perform tests on Applied Controls API endpoint without authentication"""

    client = APIClient()

    def test_get_applied_controls(self):
        """test to get applied controls from the API without authentication"""

        EndpointTestsQueries.get_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
        )

    def test_create_applied_controls(self):
        """test to create applied controls with the API without authentication"""

        EndpointTestsQueries.create_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test").id,
            },
        )

    def test_update_applied_controls(self):
        """test to update applied controls with the API without authentication"""

        EndpointTestsQueries.update_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test"),
            },
            {
                "name": "new " + APPLIED_CONTROL_NAME,
                "description": "new " + APPLIED_CONTROL_DESCRIPTION,
                "folder": Folder.objects.create(name="test2").id,
            },
        )

    def test_delete_applied_controls(self):
        """test to delete applied controls with the API without authentication"""

        EndpointTestsQueries.delete_object(
            self.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "folder": Folder.objects.create(name="test"),
            },
        )


@pytest.mark.django_db
class TestAppliedControlsAuthenticated:
    """Perform tests on Applied Controls API endpoint with authentication"""

    def test_get_applied_controls(self, test):
        """test to get applied controls from the API with authentication"""

        EndpointTestsQueries.Auth.get_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS._value_,
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "cost": APPLIED_CONTROL_COST,
                "folder": test.folder,
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "reference_control": None,
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS._value_,
                "effort": APPLIED_CONTROL_EFFORT[1],
                "is_assigned": False,
            },
            user_group=test.user_group,
        )

    def test_create_applied_controls(self, test):
        """test to create applied controls with the API with authentication"""

        reference_control = ReferenceControl.objects.create(
            name="test", typical_evidence={}, folder=Folder.objects.create(name="test2")
        )

        EndpointTestsQueries.Auth.create_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS._value_,
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "cost": APPLIED_CONTROL_COST,
                "folder": str(test.folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS._value_,
                "effort": APPLIED_CONTROL_EFFORT[1],
                "is_assigned": False,
            },
            user_group=test.user_group,
            scope=str(test.folder),
        )

    def test_update_applied_controls(self, test):
        """test to update applied controls with the API with authentication"""

        folder = Folder.objects.create(name="test2")
        reference_control = ReferenceControl.objects.create(
            name="test", typical_evidence={}, folder=folder
        )

        EndpointTestsQueries.Auth.update_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "description": APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY[0],
                "status": APPLIED_CONTROL_STATUS._value_,
                "link": APPLIED_CONTROL_LINK,
                "eta": APPLIED_CONTROL_ETA,
                "effort": APPLIED_CONTROL_EFFORT[0],
                "cost": APPLIED_CONTROL_COST,
                "folder": test.folder,
            },
            {
                "name": "new " + APPLIED_CONTROL_NAME,
                "description": "new " + APPLIED_CONTROL_DESCRIPTION,
                "category": APPLIED_CONTROL_CATEGORY2[0],
                "status": APPLIED_CONTROL_STATUS2._value_,
                "link": "new " + APPLIED_CONTROL_LINK,
                "eta": "2025-01-01",
                "effort": APPLIED_CONTROL_EFFORT2[0],
                "cost": APPLIED_CONTROL_COST2,
                "folder": str(folder.id),
            },
            {
                "folder": {"id": str(test.folder.id), "str": test.folder.name},
                "category": APPLIED_CONTROL_CATEGORY[1],
                "status": APPLIED_CONTROL_STATUS._value_,
                "effort": APPLIED_CONTROL_EFFORT[1],
                "is_assigned": False,
            },
            user_group=test.user_group,
        )

    def test_delete_applied_controls(self, test):
        """test to delete applied controls with the API with authentication"""

        EndpointTestsQueries.Auth.delete_object(
            test.client,
            "Applied controls",
            AppliedControl,
            {
                "name": APPLIED_CONTROL_NAME,
                "folder": test.folder,
            },
            user_group=test.user_group,
        )

    def test_get_effort_choices(self, test):
        """test to get applied controls effort choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "effort",
            AppliedControl.EFFORT,
            user_group=test.user_group,
        )

    def test_get_status_choices(self, test):
        """test to get applied controls status choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "status",
            AppliedControl.Status.choices,
            user_group=test.user_group,
        )

    def test_get_type_choices(self, test):
        """test to get applied controls type choices from the API with authentication"""

        EndpointTestsQueries.Auth.get_object_options(
            test.client,
            "Applied controls",
            "category",
            AppliedControl.CATEGORY,
            user_group=test.user_group,
        )


# ---------------------------------------------------------------------------
# Helpers for the IAM post-filter masking tests below.
#
# `BaseModelViewSet._filter_related_fields` masks any related-field value
# whose object lies outside the user's IAM-visible scope. Round 1 added a
# fast path that skips that masking pass when the user can already see
# every instance of every related model. The two tests below pin down
# both sides of the contract:
#
# - admin (recursive role at the global root) must see related references
#   fully serialised (no placeholder),
# - a reader scoped to a single domain folder must still get the `{}`
#   placeholder for related references that point outside that scope.
# ---------------------------------------------------------------------------


def _client_for(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _make_scoped_reader(folder):
    """User with READER role recursive on `folder` and nothing else.
    Built directly via RoleAssignment so the perimeter is exactly that
    one folder — what the masking assertions rely on."""
    user = User.objects.create_user(
        f"reader-{uuid.uuid4().hex[:6]}@perf.test", is_published=True
    )
    role = Role.objects.get(name=RoleCodename.READER.value)
    ra = RoleAssignment.objects.create(
        user=user,
        role=role,
        folder=Folder.get_root_folder(),
        is_recursive=True,
    )
    ra.perimeter_folders.add(folder)
    return user


def _setup_cross_folder_link():
    """AC in folder A; M2M-linked Asset in sibling folder B (unreachable
    to a reader scoped to A)."""
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
    ac = AppliedControl.objects.create(
        folder=folder_a, name=f"ac-{uuid.uuid4().hex[:6]}"
    )
    asset_in_b = Asset.objects.create(
        folder=folder_b,
        name=f"asset-B-{uuid.uuid4().hex[:6]}",
        type=Asset.Type.PRIMARY,
    )
    ac.assets.set([asset_in_b])
    return folder_a, folder_b, ac, asset_in_b


def _list(client, url):
    r = client.get(url)
    assert r.status_code == status.HTTP_200_OK, r.content
    body = r.json()
    return body.get("results", body) if isinstance(body, dict) else body


def _find_by_id(items, obj_id):
    target = str(obj_id)
    for it in items:
        if it.get("id") == target:
            return it
    raise AssertionError(f"id={target} not in {len(items)} list results")


@pytest.mark.django_db
class TestAppliedControlListIAMPostFilter:
    """Output equivalence for the IAM post-filter on `/api/applied-controls/`."""

    def test_admin_sees_unmasked_cross_folder_asset(self, authenticated_client):
        """Admin's recursive role at the global root covers every folder
        for every related model → fast path engages → no masking. The
        AC's `assets` M2M MUST come back with the asset's id and str."""
        _, _, ac, asset = _setup_cross_folder_link()

        items = _list(authenticated_client, "/api/applied-controls/")
        item = _find_by_id(items, ac.id)

        assets_field = item["assets"]
        assert isinstance(assets_field, list) and len(assets_field) == 1, (
            f"expected exactly one asset reference, got {assets_field!r}"
        )
        ref = assets_field[0]
        assert ref != {}, (
            "admin should see a fully-serialised asset reference, "
            f"got the post-filter placeholder: {ref!r}"
        )
        assert ref.get("id") == str(asset.id)

    def test_scoped_reader_masks_cross_folder_asset(self):
        """Slow-path correctness preserved: a reader scoped to folder A
        sees the AC (it lives in A) but the AC's `assets` references an
        asset in folder B (unreachable). `_filter_related_fields` MUST
        replace the asset dict with the `{}` placeholder."""
        folder_a, _, ac, _ = _setup_cross_folder_link()
        client = _client_for(_make_scoped_reader(folder_a))

        items = _list(client, "/api/applied-controls/")
        item = _find_by_id(items, ac.id)

        assets_field = item["assets"]
        assert isinstance(assets_field, list) and len(assets_field) == 1, (
            f"expected one masked asset reference, got {assets_field!r}"
        )
        # `BaseModelViewSet._placeholder_for` returns `{}` for hidden FKs.
        assert assets_field[0] == {}, (
            "scoped reader must NOT see the cross-folder asset's id/str; "
            f"got {assets_field[0]!r}"
        )
