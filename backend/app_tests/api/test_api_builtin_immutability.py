import pytest
from django.urls import reverse
from rest_framework import status

from core.models import Terminology
from tprm.models import Entity


@pytest.mark.django_db
class TestBuiltinImmutability:
    """Built-in objects are immutable by default; each model opts specific fields
    back in via BaseModelSerializer.BUILTIN_EDITABLE_FIELDS. Deletion is always
    blocked at the permission layer."""

    def test_builtin_terminology_visibility_editable_but_not_name(
        self, authenticated_client
    ):
        term = Terminology.objects.filter(builtin=True).first()
        assert term is not None, "startup should seed builtin terminologies"
        original_name, original_visible = term.name, term.is_visible

        url = reverse("terminologies-detail", args=[term.id])
        response = authenticated_client.patch(
            url,
            {"is_visible": not original_visible, "name": "hacked"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        term.refresh_from_db()
        assert term.is_visible == (not original_visible)  # visibility is editable
        assert term.name == original_name  # every other field stays immutable

    def test_builtin_entity_is_fully_editable(self, authenticated_client):
        entity = Entity.objects.filter(builtin=True).first()
        assert entity is not None, "startup should create the built-in Main entity"

        url = reverse("entities-detail", args=[entity.id])
        response = authenticated_client.patch(url, {"name": "Acme Corp"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        entity.refresh_from_db()
        assert entity.name == "Acme Corp"  # user-owned builtin, fully editable

    def test_builtin_object_cannot_be_deleted(self, authenticated_client):
        term = Terminology.objects.filter(builtin=True).first()
        assert term is not None

        url = reverse("terminologies-detail", args=[term.id])
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Terminology.objects.filter(id=term.id).exists()
