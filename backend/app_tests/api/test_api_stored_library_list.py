"""The stored-library list leaves each library's `content` (megabytes for the
larger ones) unread, and still tells presets apart."""

import pytest

from core.models import StoredLibrary
from library.serializers import StoredLibrarySerializer

URL = "/api/stored-libraries/"


@pytest.mark.django_db
def test_the_list_does_not_read_library_content(authenticated_client, monkeypatch):
    deferred = []
    overview = StoredLibrarySerializer.get_overview

    def spy(self, obj):
        deferred.append("content" in obj.get_deferred_fields())
        return overview(self, obj)

    monkeypatch.setattr(StoredLibrarySerializer, "get_overview", spy)
    response = authenticated_client.get(URL, {"object_type": "frameworks", "limit": 10})
    assert response.status_code == 200
    assert deferred and all(deferred)


@pytest.mark.django_db
def test_presets_are_still_flagged(authenticated_client):
    expected = StoredLibrary.objects.filter(content__preset__isnull=False).count()
    assert expected, "the shipped libraries include presets"
    rows = authenticated_client.get(URL, {"object_type": "preset", "limit": 500}).json()
    assert len(rows["results"]) == expected
    assert all(row["is_preset"] for row in rows["results"])
    others = authenticated_client.get(
        URL, {"object_type": "frameworks", "limit": 5}
    ).json()
    assert not any(row["is_preset"] for row in others["results"])
