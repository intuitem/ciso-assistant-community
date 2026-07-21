import pytest
from django.urls import reverse
from rest_framework import status

from core.models import Threat
from iam.models import Folder


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
