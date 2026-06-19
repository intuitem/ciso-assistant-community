import pytest
from rest_framework import status

from global_settings.models import GlobalSettings
from iam.models import Folder

CF_URL = "/api/custom-fields/"
PROJECTS_URL = "/api/pmbok/projects/"


@pytest.mark.django_db
class TestCustomFieldsAPI:
    """End-to-end HTTP coverage through the real router + RBAC stack."""

    @pytest.fixture(autouse=True)
    def enable_custom_fields(self, authenticated_client):
        gs, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
        )
        gs.value = {**(gs.value or {}), "custom_fields": True}
        gs.save()

    def _make_choice_def(self, client, folder_id, key="tier"):
        return client.post(
            CF_URL,
            {
                "model": "pmbok.project",
                "key": key,
                "label": "Tier",
                "field_type": "choice",
                "folder": folder_id,
                "choices": [
                    {"value": "gold", "label": "Gold"},
                    {"value": "silver", "label": "Silver"},
                ],
            },
            format="json",
        )

    def test_create_definition_with_nested_choices(self, authenticated_client):
        root = Folder.get_root_folder()
        resp = self._make_choice_def(authenticated_client, str(root.id))
        assert resp.status_code == status.HTTP_201_CREATED, resp.content

        # the read representation (retrieve) carries the localized + model fields
        detail = authenticated_client.get(f"{CF_URL}{resp.json()['id']}/").json()
        assert detail["model"] == "pmbok.project"
        assert detail["label_localized"] == "Tier"
        assert {c["value"] for c in detail["choices"]} == {"gold", "silver"}

    def test_text_field_with_empty_choices_is_accepted(self, authenticated_client):
        # the frontend schema defaults `choices` to [] even for non-choice fields
        root = Folder.get_root_folder()
        resp = authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "sensitivity",
                "label": "Sensitivity",
                "field_type": "text",
                "folder": str(root.id),
                "choices": [],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content

    def test_object_endpoint_exposes_model_for_edit_form(self, authenticated_client):
        # The edit form loads /<id>/object/ (write serializer); it must carry `model`
        # so the read-only model field can be shown.
        root = Folder.get_root_folder()
        created = self._make_choice_def(authenticated_client, str(root.id))
        obj = authenticated_client.get(f"{CF_URL}{created.json()['id']}/object/").json()
        assert obj["model"] == "pmbok.project"

    def test_searchable_rejected_on_non_text_type(self, authenticated_client):
        root = Folder.get_root_folder()
        resp = authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "cost",
                "label": "Cost",
                "field_type": "number",
                "searchable": True,
                "folder": str(root.id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "searchable" in resp.json()

    def test_same_key_different_type_rejected(self, authenticated_client):
        # A key must have one type across folders so cf__<key> resolves one column.
        root = Folder.get_root_folder()
        a = Folder.objects.create(name="Domain A", parent_folder=root)
        b = Folder.objects.create(name="Domain B", parent_folder=root)
        first = authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "priority",
                "label": "Priority",
                "field_type": "choice",
                "folder": str(a.id),
                "choices": [{"value": "high", "label": "High"}],
            },
            format="json",
        )
        assert first.status_code == status.HTTP_201_CREATED, first.content
        second = authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "priority",
                "label": "Priority",
                "field_type": "number",
                "folder": str(b.id),
            },
            format="json",
        )
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        assert "field_type" in second.json()

    def test_create_definition_without_model_is_400(self, authenticated_client):
        resp = authenticated_client.post(
            CF_URL,
            {"key": "x", "label": "X", "field_type": "text"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "model" in resp.json()

    def test_list_definitions_by_model(self, authenticated_client):
        root = Folder.get_root_folder()
        self._make_choice_def(authenticated_client, str(root.id))
        resp = authenticated_client.get(CF_URL, {"model": "pmbok.project"})
        assert resp.status_code == status.HTTP_200_OK
        keys = {d["key"] for d in resp.json()["results"]}
        assert "tier" in keys

    def test_project_roundtrip_and_filter(self, authenticated_client):
        root = Folder.get_root_folder()
        self._make_choice_def(authenticated_client, str(root.id))

        create = authenticated_client.post(
            PROJECTS_URL,
            {
                "name": "Gold project",
                "folder": str(root.id),
                "custom_fields": {"tier": "gold"},
            },
            format="json",
        )
        assert create.status_code == status.HTTP_201_CREATED, create.content
        project_id = create.json()["id"]

        detail = authenticated_client.get(f"{PROJECTS_URL}{project_id}/")
        assert detail.json()["custom_fields"] == {"tier": "gold"}

        # another project with a different value, to prove the filter discriminates
        authenticated_client.post(
            PROJECTS_URL,
            {
                "name": "Silver project",
                "folder": str(root.id),
                "custom_fields": {"tier": "silver"},
            },
            format="json",
        )
        filtered = authenticated_client.get(PROJECTS_URL, {"cf__tier": "gold"})
        names = {p["name"] for p in filtered.json()["results"]}
        assert names == {"Gold project"}

    def test_invalid_choice_value_rejected(self, authenticated_client):
        root = Folder.get_root_folder()
        self._make_choice_def(authenticated_client, str(root.id))
        resp = authenticated_client.post(
            PROJECTS_URL,
            {
                "name": "Bad",
                "folder": str(root.id),
                "custom_fields": {"tier": "platinum"},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "custom_fields" in resp.json()

    def test_disabled_flag_gates_access(self, authenticated_client):
        root = Folder.get_root_folder()
        self._make_choice_def(authenticated_client, str(root.id))
        gs = GlobalSettings.objects.get(name=GlobalSettings.Names.FEATURE_FLAGS)
        gs.value = {**gs.value, "custom_fields": False}
        gs.save()
        # reads degrade to an empty list (no hard error), writes are forbidden
        listing = authenticated_client.get(CF_URL)
        assert listing.status_code == status.HTTP_200_OK
        assert listing.json()["results"] == []
        create = self._make_choice_def(authenticated_client, str(root.id), key="nope")
        assert create.status_code == status.HTTP_403_FORBIDDEN

    def test_translations_round_trip(self, authenticated_client):
        root = Folder.get_root_folder()
        resp = authenticated_client.post(
            CF_URL,
            {
                "model": "pmbok.project",
                "key": "crit",
                "label": "Criticality",
                "field_type": "choice",
                "folder": str(root.id),
                "translations": {
                    "fr": {"label": "Criticité", "help_text": "Criticité métier"}
                },
                "choices": [
                    {
                        "value": "high",
                        "label": "High",
                        "translations": {"fr": {"label": "Élevé"}},
                    }
                ],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED, resp.content
        detail = authenticated_client.get(f"{CF_URL}{resp.json()['id']}/").json()
        assert detail["translations"] == {
            "fr": {"label": "Criticité", "help_text": "Criticité métier"}
        }
        assert detail["choices"][0]["translations"] == {"fr": {"label": "Élevé"}}

    def test_asset_host_round_trip_and_filter(self, authenticated_client):
        root = Folder.get_root_folder()
        authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "sensitivity",
                "label": "Sensitivity",
                "field_type": "text",
                "folder": str(root.id),
            },
            format="json",
        )
        create = authenticated_client.post(
            "/api/assets/",
            {
                "name": "Server",
                "folder": str(root.id),
                "type": "PR",
                "custom_fields": {"sensitivity": "high"},
            },
            format="json",
        )
        assert create.status_code == status.HTTP_201_CREATED, create.content
        asset_id = create.json()["id"]
        detail = authenticated_client.get(f"/api/assets/{asset_id}/")
        assert detail.json()["custom_fields"] == {"sensitivity": "high"}
        filtered = authenticated_client.get("/api/assets/", {"cf__sensitivity": "high"})
        assert asset_id in {a["id"] for a in filtered.json()["results"]}

    def test_search_matches_searchable_custom_field(self, authenticated_client):
        root = Folder.get_root_folder()
        authenticated_client.post(
            CF_URL,
            {
                "model": "core.asset",
                "key": "os",
                "label": "OS",
                "field_type": "text",
                "searchable": True,
                "folder": str(root.id),
            },
            format="json",
        )
        create = authenticated_client.post(
            "/api/assets/",
            {
                "name": "srv1",
                "folder": str(root.id),
                "type": "PR",
                "custom_fields": {"os": "ubuntu linux"},
            },
            format="json",
        )
        assert create.status_code == status.HTTP_201_CREATED, create.content
        hit = create.json()["id"]
        authenticated_client.post(
            "/api/assets/",
            {"name": "srv2", "folder": str(root.id), "type": "PR"},
            format="json",
        )
        result = authenticated_client.get("/api/assets/", {"search": "ubuntu"})
        ids = {a["id"] for a in result.json()["results"]}
        assert hit in ids and len(ids) == 1

    def test_applied_control_host_round_trip(self, authenticated_client):
        root = Folder.get_root_folder()
        authenticated_client.post(
            CF_URL,
            {
                "model": "core.appliedcontrol",
                "key": "vendor",
                "label": "Vendor",
                "field_type": "text",
                "folder": str(root.id),
            },
            format="json",
        )
        create = authenticated_client.post(
            "/api/applied-controls/",
            {
                "name": "AC",
                "folder": str(root.id),
                "custom_fields": {"vendor": "acme"},
            },
            format="json",
        )
        assert create.status_code == status.HTTP_201_CREATED, create.content
        cid = create.json()["id"]
        detail = authenticated_client.get(f"/api/applied-controls/{cid}/")
        assert detail.json()["custom_fields"] == {"vendor": "acme"}

    def test_for_folder_resolution(self, authenticated_client):
        root = Folder.get_root_folder()
        domain = Folder.objects.create(name="Domain A", parent_folder=root)

        # global field + a domain-scoped field, same model
        self._make_choice_def(authenticated_client, str(root.id), key="global_tier")
        authenticated_client.post(
            CF_URL,
            {
                "model": "pmbok.project",
                "key": "domain_only",
                "label": "D",
                "field_type": "text",
                "folder": str(domain.id),
            },
            format="json",
        )

        in_domain = authenticated_client.get(
            CF_URL, {"model": "pmbok.project", "for_folder": str(domain.id)}
        ).json()["results"]
        in_root = authenticated_client.get(
            CF_URL, {"model": "pmbok.project", "for_folder": str(root.id)}
        ).json()["results"]

        assert {d["key"] for d in in_domain} == {"global_tier", "domain_only"}
        assert {d["key"] for d in in_root} == {"global_tier"}  # domain field hidden
