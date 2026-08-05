import uuid

import pytest
from django.contrib.contenttypes.models import ContentType
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import ComplianceAssessment, Framework, SavedFilter
from core.utils import RoleCodename
from iam.models import Folder, Role, RoleAssignment, User

SAVED_FILTERS_URL = "/api/saved-filters/"


def _client_for(user):
    client = APIClient()
    _, token = AuthToken.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def _make_domain(name):
    return Folder.objects.create(
        name=f"{name}-{uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def _make_role_user(folder, role_codename):
    user = User.objects.create_user(
        f"user-{uuid.uuid4().hex[:6]}@tests.com", is_published=True
    )
    role = Role.objects.get(name=role_codename)
    ra = RoleAssignment.objects.create(
        user=user, role=role, folder=Folder.get_root_folder(), is_recursive=True
    )
    ra.perimeter_folders.add(folder)
    return user


def _make_framework():
    name = f"fw-{uuid.uuid4().hex[:6]}"
    return Framework.objects.create(
        folder=Folder.get_root_folder(),
        name=name,
        provider="test",
        urn=f"urn:test:framework:{uuid.uuid4().hex[:12]}",
        ref_id=name,
        min_score=0,
        max_score=4,
    )


def _make_audit(folder, framework):
    name = f"audit-{uuid.uuid4().hex[:6]}"
    return ComplianceAssessment.objects.create(
        folder=folder, framework=framework, name=name, ref_id=name
    )


def _compliance_assessment_content_type():
    return ContentType.objects.get_for_model(ComplianceAssessment)


@pytest.mark.django_db
class TestSavedFilterPermissions:
    """Only a domain manager (or admin) may write a shared SavedFilter in
    their domain -- standard add_/change_/delete_savedfilter permissions,
    same RBAC stack as every other domain-scoped model."""

    def test_domain_manager_can_create_shared_filter(self, authenticated_client):
        domain = _make_domain("d1")
        manager = _make_role_user(domain, RoleCodename.DOMAIN_MANAGER.value)
        resp = _client_for(manager).post(
            SAVED_FILTERS_URL,
            {
                "name": "my shared filter",
                "folder": str(domain.id),
                "model": "core.complianceassessment",
                "properties": {"status": [{"value": "in_progress"}]},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content

    def test_analyst_cannot_create_shared_filter(self, authenticated_client):
        domain = _make_domain("d2")
        analyst = _make_role_user(domain, RoleCodename.ANALYST.value)
        resp = _client_for(analyst).post(
            SAVED_FILTERS_URL,
            {
                "name": "nope",
                "folder": str(domain.id),
                "model": "core.complianceassessment",
                "properties": {},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_analyst_cannot_update_or_delete_shared_filter(self, authenticated_client):
        domain = _make_domain("d3")
        analyst = _make_role_user(domain, RoleCodename.ANALYST.value)
        sf = SavedFilter.objects.create(
            name="shared",
            folder=domain,
            content_type=_compliance_assessment_content_type(),
            properties={},
        )
        client = _client_for(analyst)

        resp = client.patch(
            f"{SAVED_FILTERS_URL}{sf.id}/", {"name": "hacked"}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        resp = client.delete(f"{SAVED_FILTERS_URL}{sf.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSavedFilterReferenceVisibility:
    """A shared filter referencing an object the requester cannot read must
    not appear in their list, even though the filter's own domain is
    visible to them (SavedFilterViewSet._is_visible)."""

    def test_reader_without_access_to_referenced_audit_does_not_see_filter(
        self, authenticated_client
    ):
        domain_a = _make_domain("visible")
        domain_b = _make_domain("hidden")
        framework = _make_framework()
        audit_b = _make_audit(domain_b, framework)

        sf = SavedFilter.objects.create(
            name="filter on audit B",
            folder=domain_a,
            content_type=_compliance_assessment_content_type(),
            properties={"id": [{"value": str(audit_b.id)}]},
        )

        reader = _make_role_user(domain_a, RoleCodename.READER.value)
        resp = _client_for(reader).get(SAVED_FILTERS_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()["results"]}
        assert str(sf.id) not in ids

    def test_reader_with_access_to_referenced_audit_sees_filter(
        self, authenticated_client
    ):
        domain_a = _make_domain("visible2")
        framework = _make_framework()
        audit_a = _make_audit(domain_a, framework)

        sf = SavedFilter.objects.create(
            name="filter on audit A",
            folder=domain_a,
            content_type=_compliance_assessment_content_type(),
            properties={"id": [{"value": str(audit_a.id)}]},
        )

        reader = _make_role_user(domain_a, RoleCodename.READER.value)
        resp = _client_for(reader).get(SAVED_FILTERS_URL)
        assert resp.status_code == status.HTTP_200_OK
        ids = {item["id"] for item in resp.json()["results"]}
        assert str(sf.id) in ids


@pytest.mark.django_db
class TestPersonalSavedFilters:
    """Personal filters bypass the SavedFilter table/RBAC entirely -- CRUD
    goes through /api/saved-filters/personal/ against request.user.preferences."""

    def test_crud_via_personal_endpoint(self, authenticated_client):
        domain = _make_domain("personal")
        reader = _make_role_user(domain, RoleCodename.READER.value)
        client = _client_for(reader)

        resp = client.post(
            f"{SAVED_FILTERS_URL}personal/",
            {
                "name": "p1",
                "model": "core.complianceassessment",
                "properties": {"status": [{"value": "in_progress"}]},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content
        entry_id = resp.json()["id"]

        resp = client.get(f"{SAVED_FILTERS_URL}personal/")
        assert resp.status_code == status.HTTP_200_OK
        assert any(e["id"] == entry_id for e in resp.json())

        resp = client.patch(
            f"{SAVED_FILTERS_URL}personal/{entry_id}/", {"name": "renamed"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert resp.json()["name"] == "renamed"

        resp = client.delete(f"{SAVED_FILTERS_URL}personal/{entry_id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        resp = client.get(f"{SAVED_FILTERS_URL}personal/")
        assert not any(e["id"] == entry_id for e in resp.json())


@pytest.mark.django_db
class TestSavedFilterSync:
    def test_sync_updates_personal_filter_from_shared(self, authenticated_client):
        domain = _make_domain("sync")
        manager = _make_role_user(domain, RoleCodename.DOMAIN_MANAGER.value)
        sf = SavedFilter.objects.create(
            name="shared",
            folder=domain,
            content_type=_compliance_assessment_content_type(),
            properties={"status": [{"value": "in_progress"}]},
        )
        entry = manager.add_saved_filter(
            name="my copy",
            model="core.complianceassessment",
            properties=sf.properties,
            shared_id=str(sf.id),
        )

        sf.properties = {"status": [{"value": "done"}]}
        sf.save()

        resp = _client_for(manager).post(f"{SAVED_FILTERS_URL}sync/")
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert entry["id"] in resp.json()["refreshed"]

        manager.refresh_from_db()
        updated_entry = next(
            e for e in manager.get_saved_filters() if e["id"] == entry["id"]
        )
        assert updated_entry["properties"] == {"status": [{"value": "done"}]}

    def test_sync_does_not_leak_filter_the_user_lost_access_to(
        self, authenticated_client
    ):
        domain_a = _make_domain("sync-a")
        domain_b = _make_domain("sync-b")
        framework = _make_framework()
        audit_b = _make_audit(domain_b, framework)

        sf = SavedFilter.objects.create(
            name="shared",
            folder=domain_a,
            content_type=_compliance_assessment_content_type(),
            properties={"id": [{"value": str(audit_b.id)}]},
        )
        reader = _make_role_user(domain_a, RoleCodename.READER.value)
        entry = reader.add_saved_filter(
            name="my copy",
            model="core.complianceassessment",
            properties={"status": [{"value": "in_progress"}]},
            shared_id=str(sf.id),
        )

        sf.properties = {
            "id": [{"value": str(audit_b.id)}],
            "status": [{"value": "done"}],
        }
        sf.save()

        resp = _client_for(reader).post(f"{SAVED_FILTERS_URL}sync/")
        assert resp.status_code == status.HTTP_200_OK, resp.content
        assert entry["id"] not in resp.json()["refreshed"]

        reader.refresh_from_db()
        untouched_entry = next(
            e for e in reader.get_saved_filters() if e["id"] == entry["id"]
        )
        assert untouched_entry["properties"] == {
            "status": [{"value": "in_progress"}]
        }
