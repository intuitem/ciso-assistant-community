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
    """Unit tests for StakeholderOrderingFilter ordering and field validation."""

    def _make_filter_with_ordering(self, ordering_param):
        """Return a (filter_instance, request_mock, queryset_mock, view_mock) tuple
        where the request carries the given ordering query string."""
        f = StakeholderOrderingFilter()
        f.ordering_fields = "__all__"

        request = MagicMock()
        request.query_params = {"ordering": ordering_param}

        view = MagicMock()
        view.ordering_fields = "__all__"

        # Build mock _meta.fields so DRF's __all__ branch finds real model
        # fields.  Remapped fields (entity, criticality) are NOT included
        # here — they must pass validation via get_valid_fields override.
        model_field_names = [
            t.lstrip("-")
            for t in ordering_param.split(",")
            if t.lstrip("-") not in f.field_remap
        ]
        mock_fields = []
        for name in model_field_names:
            field = MagicMock()
            field.name = name
            field.verbose_name = name
            mock_fields.append(field)

        queryset = MagicMock()
        queryset.model._meta.fields = mock_fields
        queryset.query.annotations = {}
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
        f, request, qs, view = self._make_filter_with_ordering("current_dependency")
        result = f.get_ordering(request, qs, view)
        assert result == ["current_dependency"]

    def test_criticality_field_remapped_to_annotation(self):
        f, request, qs, view = self._make_filter_with_ordering("current_criticality")
        result = f.get_ordering(request, qs, view)
        assert result == ["_current_criticality"]

    def test_descending_criticality_preserves_minus_prefix(self):
        f, request, qs, view = self._make_filter_with_ordering("-residual_criticality")
        result = f.get_ordering(request, qs, view)
        assert result == ["-_residual_criticality"]

    def test_combined_ordering_entity_and_criticality(self):
        f, request, qs, view = self._make_filter_with_ordering(
            "entity,current_criticality"
        )
        result = f.get_ordering(request, qs, view)
        assert result == ["entity__name", "_current_criticality"]
