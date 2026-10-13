import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestOptionsMetadata:
    """OPTIONS is served by DRF's SimpleMetadata, which asks the view for a
    serializer while the action is "metadata". BaseModelViewSet resolves its
    serializer through SerializerFactory, so that action has to be answered."""

    @pytest.mark.parametrize(
        "url_name",
        [
            "folders-list",
            "assets-list",
            "perimeters-list",
            "frameworks-list",
            "risk-matrices-list",
            "document-attachments-list",
        ],
    )
    def test_options_on_collection_endpoint(self, authenticated_client, url_name):
        response = authenticated_client.options(reverse(url_name))

        assert response.status_code == status.HTTP_200_OK
