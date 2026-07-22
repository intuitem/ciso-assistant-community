"""
Tests for the reusable nullable filter classes:
  - NullableModelMultipleChoiceField  (form-field validation layer)
  - NullableModelChoiceFilter         (M2M / FK filter — uses the field above)
  - NullableChoiceFilter              (CharField / IntegerField filter)

These classes are used across several FilterSets; testing them independently
avoids duplicating filter-logic tests for every model that adopts them.
"""

import pytest
from unittest.mock import patch, MagicMock
from django import forms
from django.http import QueryDict

import django_filters as df

from core.models import Actor, AppliedControl, Evidence
from core.views import (
    NullableChoiceFilter,
    NullableModelChoiceFilter,
    NullableModelMultipleChoiceField,
)
from iam.models import Folder, User


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def folder(db):
    root = Folder.objects.get(content_type=Folder.ContentType.ROOT)
    return Folder.objects.create(parent_folder=root, name="nullable-filter-test")


@pytest.fixture
def actor(db):
    user = User.objects.create_user(email="nullable_filter@example.com")
    return user.actor


# ---------------------------------------------------------------------------
# Minimal inline FilterSets used only in these tests
# ---------------------------------------------------------------------------


class _OwnerFilterSet(df.FilterSet):
    """Minimal filterset exercising NullableModelChoiceFilter on a M2M field."""

    owner = NullableModelChoiceFilter(queryset=Actor.objects.all())

    class Meta:
        model = Evidence
        fields = []


class _CategoryFilterSet(df.FilterSet):
    """Minimal filterset exercising NullableChoiceFilter on a nullable CharField."""

    category = NullableChoiceFilter(choices=AppliedControl.CATEGORY)

    class Meta:
        model = AppliedControl
        fields = []


def make_owner_filterset(query_string):
    return _OwnerFilterSet(
        data=QueryDict(query_string),
        queryset=Evidence.objects.all(),
    )


def make_category_filterset(query_string):
    return _CategoryFilterSet(
        data=QueryDict(query_string),
        queryset=AppliedControl.objects.all(),
    )


# ---------------------------------------------------------------------------
# NullableModelMultipleChoiceField
# ---------------------------------------------------------------------------


class TestNullableModelMultipleChoiceField:
    """
    Unit tests for the form-field validation layer.  No DB required — we mock
    ModelMultipleChoiceField.clean() to inspect exactly what gets forwarded.
    """

    def _make_field(self):
        return NullableModelMultipleChoiceField(queryset=MagicMock())

    def test_none_is_forwarded_unchanged(self):
        field = self._make_field()
        with patch.object(
            forms.ModelMultipleChoiceField, "clean", return_value=[]
        ) as mock_clean:
            field.clean(None)
            mock_clean.assert_called_once_with(None)

    def test_sentinel_only_forwards_empty_iterable(self):
        field = self._make_field()
        with patch.object(
            forms.ModelMultipleChoiceField, "clean", return_value=[]
        ) as mock_clean:
            field.clean(["--"])
            forwarded = list(mock_clean.call_args[0][0])
            assert forwarded == []

    def test_sentinel_is_stripped_real_values_kept(self):
        field = self._make_field()
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch.object(
            forms.ModelMultipleChoiceField, "clean", return_value=[]
        ) as mock_clean:
            field.clean(["--", uuid])
            forwarded = list(mock_clean.call_args[0][0])
            assert forwarded == [uuid]
            assert "--" not in forwarded

    def test_scalar_is_normalised_to_list(self):
        field = self._make_field()
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch.object(
            forms.ModelMultipleChoiceField, "clean", return_value=[]
        ) as mock_clean:
            field.clean(uuid)
            forwarded = list(mock_clean.call_args[0][0])
            assert forwarded == [uuid]

    def test_multiple_sentinels_are_all_stripped(self):
        field = self._make_field()
        uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch.object(
            forms.ModelMultipleChoiceField, "clean", return_value=[]
        ) as mock_clean:
            field.clean(["--", "--", uuid])
            forwarded = list(mock_clean.call_args[0][0])
            assert forwarded == [uuid]


# ---------------------------------------------------------------------------
# NullableModelChoiceFilter  (M2M / FK field — uses Evidence.owner)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNullableModelChoiceFilter:
    @pytest.fixture(autouse=True)
    def _setup(self, folder, actor):
        self.ev_owned = Evidence.objects.create(name="owned", folder=folder)
        self.ev_owned.owner.add(actor)
        self.ev_orphan = Evidence.objects.create(name="orphan", folder=folder)
        self.actor = actor

    def test_no_param_returns_all(self):
        qs = make_owner_filterset("").qs
        assert self.ev_owned in qs
        assert self.ev_orphan in qs

    def test_sentinel_returns_unowned_only(self):
        qs = make_owner_filterset("owner=--").qs
        assert self.ev_orphan in qs
        assert self.ev_owned not in qs

    def test_uuid_returns_owned_by_that_actor(self):
        qs = make_owner_filterset(f"owner={self.actor.id}").qs
        assert self.ev_owned in qs
        assert self.ev_orphan not in qs

    def test_sentinel_plus_uuid_returns_both(self):
        qs = make_owner_filterset(f"owner=--&owner={self.actor.id}").qs
        assert self.ev_owned in qs
        assert self.ev_orphan in qs

    def test_sentinel_is_valid_does_not_raise_400(self):
        fs = make_owner_filterset("owner=--")
        assert fs.is_valid()

    def test_unknown_uuid_is_invalid(self):
        # An unrecognised PK fails ModelMultipleChoiceField validation; the
        # filterset is invalid. What django-filter does with an invalid filterset
        # is framework behaviour — we only assert the validation result here.
        fs = make_owner_filterset("owner=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        assert not fs.is_valid()


# ---------------------------------------------------------------------------
# NullableChoiceFilter  (nullable CharField — uses AppliedControl.category)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestNullableChoiceFilter:
    @pytest.fixture(autouse=True)
    def _setup(self, folder):
        self.ac_policy = AppliedControl.objects.create(
            name="policy ac", folder=folder, category="policy"
        )
        self.ac_technical = AppliedControl.objects.create(
            name="technical ac", folder=folder, category="technical"
        )
        self.ac_no_category = AppliedControl.objects.create(
            name="uncategorised ac", folder=folder, category=None
        )

    def test_no_param_returns_all(self):
        qs = make_category_filterset("").qs
        assert self.ac_policy in qs
        assert self.ac_technical in qs
        assert self.ac_no_category in qs

    def test_specific_value_filters_correctly(self):
        qs = make_category_filterset("category=policy").qs
        assert self.ac_policy in qs
        assert self.ac_technical not in qs
        assert self.ac_no_category not in qs

    def test_sentinel_returns_null_only(self):
        qs = make_category_filterset("category=--").qs
        assert self.ac_no_category in qs
        assert self.ac_policy not in qs
        assert self.ac_technical not in qs

    def test_sentinel_plus_value_returns_both(self):
        qs = make_category_filterset("category=--&category=policy").qs
        assert self.ac_policy in qs
        assert self.ac_no_category in qs
        assert self.ac_technical not in qs

    def test_multiple_real_values(self):
        qs = make_category_filterset("category=policy&category=technical").qs
        assert self.ac_policy in qs
        assert self.ac_technical in qs
        assert self.ac_no_category not in qs

    def test_sentinel_added_to_choices_on_init(self):
        f = NullableChoiceFilter(
            choices=[("policy", "Policy"), ("technical", "Technical")]
        )
        choice_values = [v for v, _ in f.field.choices]
        assert "--" in choice_values
        assert choice_values[0] == "--"
