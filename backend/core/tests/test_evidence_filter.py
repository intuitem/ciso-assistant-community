import pytest
from django.http import QueryDict

from core.models import Evidence
from core.views import EvidenceFilterSet
from iam.models import Folder, User


@pytest.fixture
def folder(db):
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    return Folder.objects.create(parent_folder=root, name="evidence-filter-test")


@pytest.fixture
def actor(db):
    user = User.objects.create_user(email="evidence_filter@example.com")
    return user.actor


@pytest.fixture
def ev_owned(folder, actor):
    ev = Evidence.objects.create(name="owned evidence", folder=folder)
    ev.owner.add(actor)
    return ev


@pytest.fixture
def ev_orphan(folder):
    return Evidence.objects.create(name="orphan evidence", folder=folder)


def make_filterset(query_string):
    return EvidenceFilterSet(
        data=QueryDict(query_string),
        queryset=Evidence.objects.all(),
    )


@pytest.mark.django_db
class TestEvidenceOwnerFilter:
    def test_no_params_returns_all(self, ev_owned, ev_orphan):
        qs = make_filterset("").qs
        assert ev_owned in qs
        assert ev_orphan in qs

    def test_null_sentinel_returns_unowned_only(self, ev_owned, ev_orphan):
        qs = make_filterset("owner=--").qs
        assert ev_orphan in qs
        assert ev_owned not in qs

    def test_uuid_returns_owned_by_that_actor(self, ev_owned, ev_orphan, actor):
        qs = make_filterset(f"owner={actor.id}").qs
        assert ev_owned in qs
        assert ev_orphan not in qs

    def test_null_plus_uuid_returns_both(self, ev_owned, ev_orphan, actor):
        qs = make_filterset(f"owner=--&owner={actor.id}").qs
        assert ev_owned in qs
        assert ev_orphan in qs

    def test_null_sentinel_is_valid(self, db):
        # Regression: the old auto-generated ModelMultipleChoiceFilter raised a
        # ValidationError for '--', causing the API to return 400.
        fs = make_filterset("owner=--")
        assert fs.is_valid()


@pytest.mark.django_db
class TestEvidenceStatusFilter:
    def test_status_value_filters_correctly(self, folder):
        draft = Evidence.objects.create(
            name="draft ev", folder=folder, status=Evidence.Status.DRAFT
        )
        approved = Evidence.objects.create(
            name="approved ev", folder=folder, status=Evidence.Status.APPROVED
        )
        qs = make_filterset("status=draft").qs
        assert draft in qs
        assert approved not in qs

    def test_null_sentinel_returns_empty_for_non_nullable_status(self, folder):
        # status always has a value (default=DRAFT), so '--' (isnull) matches nothing
        Evidence.objects.create(name="ev", folder=folder)
        assert make_filterset("status=--").qs.count() == 0
