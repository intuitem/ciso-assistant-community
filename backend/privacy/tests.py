import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from core.views import SmartOrderingFilter
from iam.models import Folder
from privacy.models import Processing
from privacy.views import ProcessingViewSet


@pytest.mark.django_db
def test_processing_ref_id_sorts_naturally():
    """ref_id ("1.2", "10.1", ...) must sort numerically per segment, not as
    plain strings, otherwise "10.1" lands before "2.1"."""
    folder = Folder.objects.create(
        parent_folder=Folder.get_root_folder(), name="RefIdSortFolder"
    )
    ref_ids = ["1.1", "1.2", "1.10", "2.1", "10.1", "2.3"]
    for ref_id in ref_ids:
        Processing.objects.create(
            name=f"Processing {ref_id}", ref_id=ref_id, folder=folder
        )

    qs = Processing.objects.filter(folder=folder)
    view = ProcessingViewSet()
    request = Request(APIRequestFactory().get("/", {"ordering": "ref_id"}))

    ordered = SmartOrderingFilter().filter_queryset(request, qs, view)
    assert list(ordered.values_list("ref_id", flat=True)) == [
        "1.1",
        "1.2",
        "1.10",
        "2.1",
        "2.3",
        "10.1",
    ]
