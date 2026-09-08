import pytest
from django.conf import settings
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from core.pagination import CustomLimitOffsetPagination
from core.models import Vulnerability
from core.views import SmartOrderingFilter
from iam.models import Folder

from .fixtures import domain_perimeter_fixture  # noqa: F401


def request_with(params):
    return Request(APIRequestFactory().get("/", params))


class TestCustomLimitOffsetPagination:
    def test_default_limit_is_paginate_by(self):
        paginator = CustomLimitOffsetPagination()
        assert paginator.get_limit(request_with({})) == settings.PAGINATE_BY

    def test_limit_above_max_is_clamped(self):
        paginator = CustomLimitOffsetPagination()
        request = request_with({"limit": str(settings.PAGINATE_MAX * 10)})
        assert paginator.get_limit(request) == settings.PAGINATE_MAX

    def test_default_page_size_cannot_exceed_the_ceiling(self):
        assert settings.PAGINATE_BY <= settings.PAGINATE_MAX

    def test_explicit_limit_below_max_is_honored(self):
        paginator = CustomLimitOffsetPagination()
        assert paginator.get_limit(request_with({"limit": "50"})) == 50

    def test_invalid_limits_are_rejected(self):
        # limit=0 never meant "no limit" (stock DRF silently fell back to the
        # default page size); invalid values now fail loudly instead.
        paginator = CustomLimitOffsetPagination()
        for bad in ("0", "-5", "abc"):
            with pytest.raises(ValidationError):
                paginator.get_limit(request_with({"limit": bad}))

    def test_invalid_offsets_are_rejected(self):
        paginator = CustomLimitOffsetPagination()
        for bad in ("-1", "abc"):
            with pytest.raises(ValidationError):
                paginator.get_offset(request_with({"offset": bad}))

    def test_valid_offset_is_honored(self):
        paginator = CustomLimitOffsetPagination()
        assert paginator.get_offset(request_with({"offset": "0"})) == 0
        assert paginator.get_offset(request_with({"offset": "120"})) == 120
        assert paginator.get_offset(request_with({})) == 0


class OrderedByNameView:
    ordering = ["name"]
    ordering_fields = ["name", "folder"]


class TestSmartOrderingTiebreaker:
    def test_default_ordering_gains_pk_tiebreaker(self):
        ordering = SmartOrderingFilter().get_ordering(
            request_with({}), None, OrderedByNameView
        )
        assert ordering == ["name", "pk"]

    def test_existing_pk_or_id_term_is_not_duplicated(self):
        class View:
            ordering = ["-is_active", "email", "id"]
            ordering_fields = ["is_active", "email", "id"]

        ordering = SmartOrderingFilter().get_ordering(request_with({}), None, View)
        assert ordering == ["-is_active", "email", "id"]

    def test_query_param_ordering_gains_pk_tiebreaker(self):
        ordering = SmartOrderingFilter().get_ordering(
            request_with({"ordering": "-name"}), None, OrderedByNameView
        )
        assert ordering == ["-name", "pk"]

    def test_folder_alias_maps_and_gains_pk_tiebreaker(self):
        ordering = SmartOrderingFilter().get_ordering(
            request_with({"ordering": "folder"}), None, OrderedByNameView
        )
        assert ordering == ["folder__name", "pk"]

    def test_folder_alias_skipped_without_folder_relation(self):
        # Views exposing a string `folder` annotation (e.g. the audit log)
        # must order on the annotation, not a nonexistent relation.
        class AnnotatedFolderView:
            ordering = ["name"]
            ordering_fields = ["folder", "name"]

        ordering = SmartOrderingFilter().get_ordering(
            request_with({"ordering": "folder"}),
            Folder.objects.all(),
            AnnotatedFolderView,
        )
        assert ordering == ["folder", "pk"]

    @pytest.mark.django_db
    def test_offset_paging_is_lossless_when_sort_keys_tie(
        self, domain_perimeter_fixture
    ):
        folder = Folder.objects.filter(content_type=Folder.ContentType.DOMAIN).first()
        # Names are scope-unique, so tie the rows on severity instead: every
        # row keeps the default severity, making the sort key identical.
        created = [
            Vulnerability.objects.create(name=f"vuln-{i}", folder=folder)
            for i in range(6)
        ]

        class OrderedBySeverityView:
            ordering = ["severity"]
            ordering_fields = ["severity"]

        ordering_filter = SmartOrderingFilter()
        seen = []
        for offset in (0, 2, 4):
            # Fresh queryset per window: each page of a paginated list view
            # is a separate SQL query.
            qs = ordering_filter.filter_queryset(
                request_with({}),
                Vulnerability.objects.all(),
                OrderedBySeverityView,
            )
            seen += [
                str(pk) for pk in qs.values_list("id", flat=True)[offset : offset + 2]
            ]

        assert sorted(seen) == sorted(str(v.id) for v in created)
