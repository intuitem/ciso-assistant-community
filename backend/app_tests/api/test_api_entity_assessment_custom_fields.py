import pytest
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APIClient

from core.models import ComplianceAssessment, Framework, Perimeter, User
from core.utils import RoleCodename
from global_settings import utils as ff_utils
from global_settings.models import GlobalSettings
from global_settings.utils import clear_feature_flags_cache
from iam.models import Folder, Role, RoleAssignment, UserGroup
from tprm.models import Entity, EntityAssessment

CF_URL = "/api/custom-fields/"
EA_URL = "/api/entity-assessments/"


def _client_for(user: User) -> APIClient:
    client = APIClient()
    token = AuthToken.objects.create(user=user)[1]
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.mark.django_db
class TestEntityAssessmentCustomFields:
    @pytest.fixture(autouse=True)
    def enable_custom_fields(self, authenticated_client, monkeypatch):
        supported = ff_utils.get_supported_feature_flags() | {"custom_fields"}
        monkeypatch.setattr(ff_utils, "get_supported_feature_flags", lambda: supported)
        gs, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
        )
        gs.value = {**(gs.value or {}), "custom_fields": True}
        gs.save()
        clear_feature_flags_cache()

    @pytest.fixture
    def domains(self, authenticated_client):
        root = Folder.get_root_folder()
        domain_a = Folder.objects.create(name="Domain A", parent_folder=root)
        domain_b = Folder.objects.create(name="Domain B", parent_folder=root)
        perimeter_a = Perimeter.objects.create(name="Perimeter A", folder=domain_a)
        perimeter_b = Perimeter.objects.create(name="Perimeter B", folder=domain_b)
        entity = Entity.objects.create(name="Vendor", folder=domain_b)
        return {
            "a": domain_a,
            "b": domain_b,
            "perimeter_a": perimeter_a,
            "perimeter_b": perimeter_b,
            "entity": entity,
        }

    def _make_text_def(self, client, folder, key, required=False):
        resp = client.post(
            CF_URL,
            {
                "model": "tprm.entityassessment",
                "key": key,
                "label": key,
                "field_type": "text",
                "required": required,
                "folder": str(folder.id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content

    def _create_assessment(self, client, domains, **extra):
        resp = client.post(
            EA_URL,
            {"name": "Round 1", "entity": str(domains["entity"].id), **extra},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content
        return resp.json()["id"]

    def test_round_trip_on_detail(self, authenticated_client, domains):
        self._make_text_def(authenticated_client, domains["b"], "vendor_tier")
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(domains["b"].id),
            custom_fields={"vendor_tier": "gold"},
        )

        detail = authenticated_client.get(f"{EA_URL}{ea_id}/")
        assert detail.json()["custom_fields"] == {"vendor_tier": "gold"}

    def test_create_with_root_folder_follows_perimeter(
        self, authenticated_client, domains
    ):
        self._make_text_def(authenticated_client, domains["b"], "vendor_tier")
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(Folder.get_root_folder().id),
            perimeter=str(domains["perimeter_b"].id),
            custom_fields={"vendor_tier": "gold"},
        )

        ea = EntityAssessment.objects.get(pk=ea_id)
        assert ea.folder == domains["b"]
        assert ea.custom_fields == {"vendor_tier": "gold"}

    def test_explicit_folder_wins_over_resent_perimeter(
        self, authenticated_client, domains
    ):
        self._make_text_def(authenticated_client, domains["b"], "vendor_tier")
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(domains["b"].id),
            perimeter=str(domains["perimeter_a"].id),
            custom_fields={"vendor_tier": "gold"},
        )

        # What the edit form sends: folder and unchanged perimeter.
        resp = authenticated_client.patch(
            f"{EA_URL}{ea_id}/",
            {
                "folder": str(domains["b"].id),
                "perimeter": str(domains["perimeter_a"].id),
                "custom_fields": {"vendor_tier": "silver"},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content

        ea = EntityAssessment.objects.get(pk=ea_id)
        assert ea.folder == domains["b"]
        assert ea.custom_fields == {"vendor_tier": "silver"}

    def test_perimeter_move_enforces_destination_required_fields(
        self, authenticated_client, domains
    ):
        self._make_text_def(
            authenticated_client, domains["b"], "vendor_tier", required=True
        )
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(domains["a"].id),
            perimeter=str(domains["perimeter_a"].id),
        )

        resp = authenticated_client.patch(
            f"{EA_URL}{ea_id}/",
            {"perimeter": str(domains["perimeter_b"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.content
        assert "vendor_tier" in resp.json()["custom_fields"]

        resp = authenticated_client.patch(
            f"{EA_URL}{ea_id}/",
            {
                "perimeter": str(domains["perimeter_b"].id),
                "custom_fields": {"vendor_tier": "gold"},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK, resp.content

        ea = EntityAssessment.objects.get(pk=ea_id)
        assert ea.folder == domains["b"]
        assert ea.custom_fields == {"vendor_tier": "gold"}

    def test_perimeter_move_requires_add_permission_on_destination(
        self, authenticated_client, domains
    ):
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(domains["b"].id),
            perimeter=str(domains["perimeter_b"].id),
        )

        user = User.objects.create_user("analyst-b@tests.com")
        group = UserGroup.objects.create(name="B analysts", folder=domains["b"])
        group.user_set.add(user)
        ra = RoleAssignment.objects.create(
            user_group=group,
            role=Role.objects.get(name=str(RoleCodename.ANALYST)),
            folder=domains["b"],
            is_recursive=True,
        )
        ra.perimeter_folders.add(domains["b"])

        resp = _client_for(user).patch(
            f"{EA_URL}{ea_id}/",
            {"perimeter": str(domains["perimeter_a"].id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN, resp.content
        assert EntityAssessment.objects.get(pk=ea_id).folder == domains["b"]

    def test_new_revision_copies_custom_fields(self, authenticated_client, domains):
        self._make_text_def(
            authenticated_client, domains["b"], "vendor_tier", required=True
        )
        ea_id = self._create_assessment(
            authenticated_client,
            domains,
            folder=str(domains["b"].id),
            custom_fields={"vendor_tier": "gold"},
        )
        framework = Framework.objects.create(name="Questionnaire", folder=domains["b"])
        audit = ComplianceAssessment.objects.create(
            name="Round 1 audit", framework=framework, folder=domains["b"]
        )
        EntityAssessment.objects.filter(pk=ea_id).update(compliance_assessment=audit)

        resp = authenticated_client.post(
            f"{EA_URL}{ea_id}/clone/",
            {"name": "Round 2", "version": "2.0"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content

        clone_id = resp.json()["id"]
        clone = EntityAssessment.objects.get(pk=clone_id)
        assert clone.custom_fields == {"vendor_tier": "gold"}
        assert EntityAssessment.objects.get(pk=ea_id).custom_fields == {
            "vendor_tier": "gold"
        }
