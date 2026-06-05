"""
Shared fixtures for all data_wizard tests.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from rest_framework.test import APIClient
from knox.models import AuthToken

from core.apps import startup
from iam.models import Folder, User, UserGroup
from data_wizard.views import BaseContext, ConflictMode


# ─────────────────────────────────────────────────────────────────────────────
# Folder hierarchy
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def root_folder(db):
    # startup() is not invoked in pytest, but some tests may have triggered it already.
    # Use get_or_create to avoid duplicate ROOT folder constraint errors.
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT,
        defaults={"name": "Global", "builtin": True},
    )
    return folder


@pytest.fixture
def domain_folder(root_folder):
    return Folder.objects.create(
        name="Test Domain",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )


@pytest.fixture
def other_folder(root_folder):
    return Folder.objects.create(
        name="Other Domain",
        parent_folder=root_folder,
        content_type=Folder.ContentType.DOMAIN,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Users & auth
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db, root_folder):
    user = User.objects.create_superuser("admin@datawizard.test", is_published=True)
    user.folder = root_folder
    user.save()
    return user


@pytest.fixture
def api_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# ─────────────────────────────────────────────────────────────────────────────
# Consumer context helpers
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def base_context(domain_folder, admin_user):
    request = MagicMock()
    request.user = admin_user
    return BaseContext(
        request=request,
        folder_id=str(domain_folder.id),
        folders_map={"test domain": str(domain_folder.id)},
        on_conflict=ConflictMode.STOP,
    )


@pytest.fixture
def skip_context(domain_folder, admin_user):
    request = MagicMock()
    request.user = admin_user
    return BaseContext(
        request=request,
        folder_id=str(domain_folder.id),
        folders_map={},
        on_conflict=ConflictMode.SKIP,
    )


@pytest.fixture
def update_context(domain_folder, admin_user):
    request = MagicMock()
    request.user = admin_user
    return BaseContext(
        request=request,
        folder_id=str(domain_folder.id),
        folders_map={},
        on_conflict=ConflictMode.UPDATE,
    )


@pytest.fixture
def app_ready(db):
    """Initialize application state (roles, groups, root folder) via startup()."""
    startup(sender=None)
    return Folder.objects.get(content_type=Folder.ContentType.ROOT)


@pytest.fixture
def knox_admin_client(app_ready):
    """
    Authenticated APIClient using a real knox token.
    The user is added to the BI-UG-ADM superuser group created by startup(),
    giving it full RBAC access across all folders — no RBAC patching needed.
    """
    admin = User.objects.create_superuser(
        "knox-admin@datawizard.test", is_published=True
    )
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)

    client = APIClient()
    _, token = AuthToken.objects.create(user=admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture
def knox_restricted_client(app_ready, root_folder):
    """
    Authenticated APIClient for a user with NO role assignments.
    get_accessible_object_ids() returns [] for this user — used to prove
    RBAC filtering is real and not a patch artifact.
    """
    user = User.objects.create_user("restricted@datawizard.test", is_published=True)
    user.folder = root_folder
    user.save()

    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


# ─────────────────────────────────────────────────────────────────────────────
# process_records patch — bypasses RoleAssignment permission checks
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def all_accessible():
    """Patch RoleAssignment so process_records sees all objects as accessible."""

    def _all_ids(root_folder, user, model_class):
        ids = list(model_class.objects.values_list("id", flat=True))
        return ids, ids, ids

    with patch(
        "data_wizard.views.RoleAssignment.get_accessible_object_ids",
        side_effect=_all_ids,
    ):
        yield


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_csv_file(content: str, filename: str = "test.csv") -> io.BytesIO:
    buf = io.BytesIO(content.encode())
    buf.name = filename
    return buf


def make_excel_file(
    data: dict[str, list[dict]], filename: str = "test.xlsx"
) -> io.BytesIO:
    """Create a minimal in-memory Excel file with one sheet per key."""
    import openpyxl

    wb = openpyxl.Workbook()
    first = True
    for sheet_name, rows in data.items():
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(sheet_name)
        if not rows:
            continue
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = filename
    return buf
