import pytest
from rest_framework import status

from core.models import Evidence, EvidenceRevision
from iam.models import Folder

URL = "/api/evidence-revisions/"


@pytest.mark.django_db
class TestEvidenceRevisionsSearch:
    """``?search=`` must not 500 on a model without ``name``/``description``."""

    @pytest.fixture
    def revision(self):
        folder = Folder.objects.create(name="test")
        evidence = Evidence.objects.create(name="Pentest report", folder=folder)
        return EvidenceRevision.objects.create(
            evidence=evidence, version=1, observation="Scope was reduced"
        )

    def test_search_returns_200(self, authenticated_client, revision):
        response = authenticated_client.get(URL, {"search": "foo"})
        assert response.status_code == status.HTTP_200_OK

    def test_search_matches_observation(self, authenticated_client, revision):
        response = authenticated_client.get(URL, {"search": "reduced"})
        assert response.status_code == status.HTTP_200_OK
        assert [r["id"] for r in response.json()["results"]] == [str(revision.id)]

    def test_search_matches_evidence_name(self, authenticated_client, revision):
        response = authenticated_client.get(URL, {"search": "pentest"})
        assert response.status_code == status.HTTP_200_OK
        assert [r["id"] for r in response.json()["results"]] == [str(revision.id)]

    def test_search_no_match(self, authenticated_client, revision):
        response = authenticated_client.get(URL, {"search": "nomatch"})
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"] == []
