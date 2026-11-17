"""Tests for the ref_id filter on /api/folders/."""

import pytest
from rest_framework import status

from iam.models import Folder

ENDPOINT = "/api/folders/"


def _ids(response) -> set[str]:
    assert response.status_code == status.HTTP_200_OK, response.content
    return {row["id"] for row in response.json()["results"]}


@pytest.mark.django_db
class TestFolderRefIdFilter:
    @pytest.fixture
    def folders(self):
        root = Folder.get_root_folder()
        it = Folder.objects.create(name="IT", ref_id="DOM.IT", parent_folder=root)
        Folder.objects.create(name="IT ops", ref_id="DOM.IT2", parent_folder=it)
        Folder.objects.create(name="DOM.IT named", parent_folder=root)
        return it

    def test_returns_only_the_exact_match(self, authenticated_client, folders):
        response = authenticated_client.get(ENDPOINT, {"ref_id": "DOM.IT"})
        assert _ids(response) == {str(folders.id)}

    def test_ignores_case_and_padding(self, authenticated_client, folders):
        response = authenticated_client.get(ENDPOINT, {"ref_id": "  dom.it "})
        assert _ids(response) == {str(folders.id)}

    def test_matches_a_padded_value_stored_past_clean(
        self, authenticated_client, folders
    ):
        Folder.objects.filter(pk=folders.pk).update(ref_id="\tDOM.IT ")
        response = authenticated_client.get(ENDPOINT, {"ref_id": "dom.it"})
        assert _ids(response) == {str(folders.id)}

    def test_whitespace_only_value_matches_nothing(self, authenticated_client, folders):
        response = authenticated_client.get(ENDPOINT, {"ref_id": "  \t "})
        assert _ids(response) == set()

    def test_non_ascii_padding_is_part_of_the_value(
        self, authenticated_client, folders
    ):
        """The index trims ASCII whitespace only, so the filter must not strip more."""
        padded = Folder.objects.create(name="Padded", parent_folder=folders)
        Folder.objects.filter(pk=padded.pk).update(ref_id="\u00a0DOM.IT\u00a0")
        response = authenticated_client.get(ENDPOINT, {"ref_id": "\u00a0DOM.IT\u00a0"})
        assert _ids(response) == {str(padded.id)}

    def test_partial_value_matches_nothing(self, authenticated_client, folders):
        response = authenticated_client.get(ENDPOINT, {"ref_id": "DOM"})
        assert _ids(response) == set()
