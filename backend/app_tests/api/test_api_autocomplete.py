import pytest
from django.urls import reverse
from rest_framework import status

from core.models import Threat
from iam.models import Folder, UserGroup


def _rows(response):
    return (
        response.data["results"] if isinstance(response.data, dict) else response.data
    )


@pytest.mark.django_db
class TestGenericAutocomplete:
    """Every BaseModelViewSet exposes the lightweight autocomplete action used
    by lazy selects and entity pickers (threats has no custom autocomplete nor
    an id filterset entry, so it exercises the generic mixin path)."""

    def test_autocomplete_available_on_plain_viewsets(self, authenticated_client):
        Threat.objects.create(name="Phishing", folder=Folder.get_root_folder())

        response = authenticated_client.get(reverse("threats-autocomplete"))

        assert response.status_code == status.HTTP_200_OK
        rows = _rows(response)
        phishing = next(r for r in rows if r["str"] == "Phishing")
        assert "id" in phishing

    def test_id_filter_hydrates_selection(self, authenticated_client):
        root = Folder.get_root_folder()
        target = Threat.objects.create(name="Target", folder=root)
        Threat.objects.create(name="Other", folder=root)

        response = authenticated_client.get(
            reverse("threats-autocomplete"), {"id": str(target.id)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert [r["id"] for r in _rows(response)] == [str(target.id)]

    def test_payload_carries_label_fields(self, authenticated_client):
        # Option labels compose ref_id/name and the folder scope client-side;
        # the lightweight payload must carry them so lazily searched options
        # render exactly like eagerly fetched ones.
        root = Folder.get_root_folder()
        Threat.objects.create(name="Phishing", ref_id="T-1", folder=root)

        response = authenticated_client.get(reverse("threats-autocomplete"))

        row = next(r for r in _rows(response) if r.get("name") == "Phishing")
        assert row["ref_id"] == "T-1"
        assert str(row["folder"]["id"]) == str(root.id)
        assert row["folder"]["str"] == str(root)

    def test_invalid_id_list_is_rejected(self, authenticated_client):
        response = authenticated_client.get(
            reverse("threats-autocomplete"), {"id": "not-a-uuid"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_folder_masking_matches_list_endpoint(self, authenticated_client):
        # Autocomplete must apply the same related-field IAM masking as the
        # list endpoint: the nested folder representation must be identical
        # for the same user + object (masked to {} when unviewable, populated
        # otherwise) — never richer via autocomplete.
        from test_utils import EndpointTestsUtils

        Threat.objects.create(
            name="Published threat",
            folder=Folder.get_root_folder(),
            is_published=True,
        )
        scoped_client, _, _ = EndpointTestsUtils.get_test_client_and_folder(
            authenticated_client, "BI-UG-AUD", "test"
        )

        list_resp = scoped_client.get(reverse("threats-list"))
        auto_resp = scoped_client.get(reverse("threats-autocomplete"))
        assert list_resp.status_code == status.HTTP_200_OK
        assert auto_resp.status_code == status.HTTP_200_OK

        def folder_of(resp):
            row = next(r for r in _rows(resp) if r.get("name") == "Published threat")
            return row["folder"]

        assert folder_of(auto_resp) == folder_of(list_resp)

    def test_user_group_autocomplete_honors_search(self, authenticated_client):
        # UserGroupViewSet has no SearchFilter: search is implemented by the
        # in-memory UserGroupFilter, which must apply to autocomplete exactly
        # like list — otherwise lazy pickers ignore the typed term.
        root = Folder.get_root_folder()
        UserGroup.objects.create(name="Blue Team", folder=root)
        UserGroup.objects.create(name="Red Team", folder=root)

        response = authenticated_client.get(
            reverse("user-groups-autocomplete"), {"search": "blue"}
        )

        assert response.status_code == status.HTTP_200_OK
        labels = [r["str"] for r in _rows(response)]
        assert any("Blue Team" in label for label in labels)
        assert not any("Red Team" in label for label in labels)

    def test_user_group_autocomplete_id_hydration(self, authenticated_client):
        # ?id= hydration must keep working now that the in-memory filter runs
        # on the autocomplete action (it turns the queryset into a list).
        root = Folder.get_root_folder()
        target = UserGroup.objects.create(name="Hydrate Me", folder=root)
        UserGroup.objects.create(name="Not Me", folder=root)

        response = authenticated_client.get(
            reverse("user-groups-autocomplete"), {"id": str(target.id)}
        )

        assert response.status_code == status.HTTP_200_OK
        assert [r["id"] for r in _rows(response)] == [str(target.id)]
