import pytest
from unittest.mock import MagicMock

from ebios_rm.models import EbiosRMStudy, Stakeholder
from ebios_rm.views import StakeholderOrderingFilter
from core.models import Terminology

from tprm.models import Entity

from ebios_rm.tests.fixtures import *


@pytest.mark.django_db
class TestStakeholder:
    @pytest.mark.usefixtures(
        "basic_ebios_rm_study_fixture",
    )
    def test_create_stakeholder_basic(self):
        study = EbiosRMStudy.objects.get(name="test study")
        entity = Entity.objects.create(name="Entity")
        category = Terminology.objects.get(
            name="supplier", field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP
        )
        stakeholder = Stakeholder.objects.create(
            entity=entity,
            category=category,
            ebios_rm_study=study,
        )

        assert stakeholder in study.stakeholders.all()
        assert stakeholder.entity == entity
        assert stakeholder.category == category

        assert stakeholder.current_criticality == 0
        assert stakeholder.residual_criticality == 0


class TestStakeholderOrderingFilter:
    """Unit tests for StakeholderOrderingFilter.get_ordering remapping logic."""

    def _make_filter_with_ordering(self, ordering_param):
        """Return a (filter_instance, request_mock, queryset_mock, view_mock) tuple
        where the request carries the given ordering query string."""
        f = StakeholderOrderingFilter()
        # ordering_fields must be set so the parent resolves the param
        f.ordering_fields = "__all__"

        request = MagicMock()
        request.query_params = {"ordering": ordering_param}

        queryset = MagicMock()
        view = MagicMock()
        view.ordering_fields = "__all__"
        # get_default_valid_fields falls back to model fields; mock it out
        f.get_default_valid_fields = MagicMock(return_value=[])
        f.get_valid_fields = MagicMock(
            return_value=[
                (t.lstrip("-"), t.lstrip("-")) for t in ordering_param.split(",")
            ]
        )
        return f, request, queryset, view

    def test_entity_field_remapped_to_entity_name(self):
        f, request, qs, view = self._make_filter_with_ordering("entity")
        result = f.get_ordering(request, qs, view)
        assert result == ["entity__name"]

    def test_descending_entity_preserves_minus_prefix(self):
        f, request, qs, view = self._make_filter_with_ordering("-entity")
        result = f.get_ordering(request, qs, view)
        assert result == ["-entity__name"]

    def test_unmapped_field_passes_through_unchanged(self):
        f, request, qs, view = self._make_filter_with_ordering("current_criticality")
        result = f.get_ordering(request, qs, view)
        assert result == ["current_criticality"]

    def test_combined_ordering_entity_and_unmapped(self):
        f, request, qs, view = self._make_filter_with_ordering(
            "entity,current_criticality"
        )
        result = f.get_ordering(request, qs, view)
        assert result == ["entity__name", "current_criticality"]
