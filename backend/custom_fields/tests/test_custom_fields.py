"""
Custom fields — phase 1 backend tests.

Exercises the public surface of custom_fields/:
- model invariants (uniqueness, typed value resolution)
- CustomFieldsMixin accessors on a host (pmbok.Project)
- CustomFieldsViewSetMixin filter injection on ProjectViewSet
- Filter cache invalidation on definition save/delete
- Serializer mixin read/write round-trip
"""

import pytest
from django.contrib.contenttypes.models import ContentType

from custom_fields.host import CustomFieldsMixin
from custom_fields.models import (
    FieldChoice,
    FieldDefinition,
    FieldValue,
)
from iam.models import Folder
from pmbok.models import Project
from pmbok.serializers import ProjectReadSerializer, ProjectWriteSerializer
from pmbok.views import ProjectViewSet


@pytest.fixture
def project_ct():
    return ContentType.objects.get_for_model(Project)


@pytest.fixture
def root_folder(db):
    folder = Folder.objects.filter(content_type=Folder.ContentType.ROOT).first()
    if folder is None:
        folder = Folder.objects.create(
            name="Global", content_type=Folder.ContentType.ROOT, builtin=True
        )
    return folder


@pytest.fixture
def criticality_definition(project_ct, db):
    d = FieldDefinition.objects.create(
        target_content_type=project_ct,
        name="criticality",
        label="Criticality",
        type=FieldDefinition.Type.SINGLE_CHOICE,
    )
    FieldChoice.objects.create(definition=d, value="low", label="Low", order=1)
    FieldChoice.objects.create(definition=d, value="medium", label="Medium", order=2)
    FieldChoice.objects.create(definition=d, value="high", label="High", order=3)
    return d


@pytest.fixture
def projects_low_med_high(root_folder, criticality_definition):
    low = Project.objects.create(name="P-low", folder=root_folder)
    med = Project.objects.create(name="P-med", folder=root_folder)
    high = Project.objects.create(name="P-high", folder=root_folder)
    low.set_custom_field("criticality", "low")
    med.set_custom_field("criticality", "medium")
    high.set_custom_field("criticality", "high")
    return low, med, high


# --- Model invariants -------------------------------------------------------


@pytest.mark.django_db
class TestModelInvariants:
    def test_definition_unique_per_content_type_and_name(self, project_ct):
        FieldDefinition.objects.create(
            target_content_type=project_ct, name="a", label="A"
        )
        with pytest.raises(Exception):
            FieldDefinition.objects.create(
                target_content_type=project_ct, name="a", label="A again"
            )

    def test_choice_unique_per_definition_and_value(self, criticality_definition):
        with pytest.raises(Exception):
            FieldChoice.objects.create(
                definition=criticality_definition, value="low", label="Dup"
            )

    def test_value_unique_per_host(
        self, criticality_definition, root_folder, project_ct
    ):
        p = Project.objects.create(name="P-unique", folder=root_folder)
        FieldValue.objects.create(
            definition=criticality_definition,
            content_type=project_ct,
            object_id=p.id,
            value_choice=criticality_definition.choices.get(value="low"),
        )
        with pytest.raises(Exception):
            FieldValue.objects.create(
                definition=criticality_definition,
                content_type=project_ct,
                object_id=p.id,
                value_choice=criticality_definition.choices.get(value="high"),
            )

    def test_resolved_value_dispatches_by_type(self, project_ct, root_folder):
        cases = [
            (FieldDefinition.Type.TEXT, {"value_text": "hello"}, "hello"),
            (FieldDefinition.Type.NUMBER, {"value_number": 42}, 42),
            (FieldDefinition.Type.BOOLEAN, {"value_boolean": True}, True),
        ]
        p = Project.objects.create(name="P-resolved", folder=root_folder)
        for d_type, kwargs, expected in cases:
            d = FieldDefinition.objects.create(
                target_content_type=project_ct,
                name=f"a_{d_type.value}",
                label="A",
                type=d_type,
            )
            v = FieldValue.objects.create(
                definition=d,
                content_type=project_ct,
                object_id=p.id,
                **kwargs,
            )
            actual = v.resolved_value
            if d_type == FieldDefinition.Type.NUMBER:
                actual = int(actual)
            assert actual == expected


# --- Host mixin accessors ---------------------------------------------------


@pytest.mark.django_db
class TestHostMixin:
    def test_set_then_read_dict(self, criticality_definition, root_folder):
        p = Project.objects.create(name="P-set-get", folder=root_folder)
        p.set_custom_field("criticality", "medium")
        assert p.custom_fields["criticality"] == "medium"

    def test_set_overwrites(self, criticality_definition, root_folder):
        p = Project.objects.create(name="P-overwrite", folder=root_folder)
        p.set_custom_field("criticality", "low")
        p.set_custom_field("criticality", "high")
        assert p.custom_fields["criticality"] == "high"
        assert (
            FieldValue.objects.filter(
                definition=criticality_definition, object_id=p.id
            ).count()
            == 1
        )

    def test_set_with_none_clears(self, criticality_definition, root_folder):
        p = Project.objects.create(name="P-clear", folder=root_folder)
        p.set_custom_field("criticality", "low")
        p.set_custom_field("criticality", None)
        assert p.custom_fields.get("criticality") is None

    def test_unknown_field_raises(self, root_folder):
        p = Project.objects.create(name="P-unknown", folder=root_folder)
        with pytest.raises(ValueError):
            p.set_custom_field("does_not_exist", "x")

    def test_unknown_choice_raises(self, criticality_definition, root_folder):
        p = Project.objects.create(name="P-bad-choice", folder=root_folder)
        with pytest.raises(FieldChoice.DoesNotExist):
            p.set_custom_field("criticality", "purple")

    def test_custom_fields_dict_includes_unset_with_default(
        self, project_ct, root_folder
    ):
        FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="phase",
            label="Phase",
            type=FieldDefinition.Type.TEXT,
            default="discovery",
        )
        p = Project.objects.create(name="P-defaults", folder=root_folder)
        assert p.custom_fields == {"phase": "discovery"}


# --- Filter mechanics -------------------------------------------------------


@pytest.mark.django_db
class TestFilterInjection:
    def _filterset(self):
        viewset = ProjectViewSet()
        return viewset.filterset_class

    def test_filter_field_is_injected(self, criticality_definition):
        fs = self._filterset()
        assert "field_criticality" in fs.declared_filters

    def test_single_choice_filter_matches(self, projects_low_med_high, root_folder):
        _, _, high = projects_low_med_high
        fs = self._filterset()
        qs = fs(
            data={"field_criticality": "high"},
            queryset=Project.objects.filter(folder=root_folder),
        ).qs
        assert list(qs.values_list("name", flat=True)) == [high.name]

    def test_single_choice_csv_matches_multiple(
        self, projects_low_med_high, root_folder
    ):
        _, med, high = projects_low_med_high
        fs = self._filterset()
        qs = fs(
            data={"field_criticality": "medium,high"},
            queryset=Project.objects.filter(folder=root_folder),
        ).qs
        assert sorted(qs.values_list("name", flat=True)) == sorted(
            [med.name, high.name]
        )

    def test_bogus_value_returns_empty(self, projects_low_med_high, root_folder):
        fs = self._filterset()
        qs = fs(
            data={"field_criticality": "nonexistent"},
            queryset=Project.objects.filter(folder=root_folder),
        ).qs
        assert list(qs) == []

    def test_combines_with_native_filter(
        self, projects_low_med_high, root_folder, criticality_definition
    ):
        _, _, high = projects_low_med_high
        fs = self._filterset()
        qs = fs(
            data={"folder": str(root_folder.id), "field_criticality": "high"},
            queryset=Project.objects.filter(folder=root_folder),
        ).qs
        assert list(qs.values_list("name", flat=True)) == [high.name]

    def test_text_filter_is_icontains(self, project_ct, root_folder):
        FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="codename",
            label="Codename",
            type=FieldDefinition.Type.TEXT,
        )
        a = Project.objects.create(name="A", folder=root_folder)
        b = Project.objects.create(name="B", folder=root_folder)
        a.set_custom_field("codename", "Phoenix")
        b.set_custom_field("codename", "Hydra")
        fs = ProjectViewSet().filterset_class
        qs = fs(
            data={"field_codename": "phoe"},
            queryset=Project.objects.filter(folder=root_folder),
        ).qs
        assert list(qs.values_list("name", flat=True)) == ["A"]


# --- Cache invalidation -----------------------------------------------------


@pytest.mark.django_db
class TestFilterFreshness:
    """Filters are rebuilt per request — newly created or deleted definitions
    appear / disappear on the next request without any cache invalidation
    machinery."""

    def test_new_definition_appears_immediately(self, project_ct, root_folder):
        first = ProjectViewSet().filterset_class
        assert "field_late" not in first.declared_filters
        FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="late",
            label="Late",
            type=FieldDefinition.Type.TEXT,
        )
        second = ProjectViewSet().filterset_class
        assert "field_late" in second.declared_filters

    def test_deleted_definition_disappears_immediately(self, criticality_definition):
        first = ProjectViewSet().filterset_class
        assert "field_criticality" in first.declared_filters
        criticality_definition.delete()
        second = ProjectViewSet().filterset_class
        assert "field_criticality" not in second.declared_filters


# --- Serializer round-trip --------------------------------------------------


@pytest.mark.django_db
class TestSerializerRoundTrip:
    def test_read_emits_custom_fields_dict(self, projects_low_med_high):
        _, _, high = projects_low_med_high
        data = ProjectReadSerializer(high).data
        assert "custom_fields" in data
        assert data["custom_fields"]["criticality"] == "high"

    def test_write_accepts_custom_fields_on_create(
        self, criticality_definition, root_folder
    ):
        payload = {
            "name": "P-via-serializer",
            "folder": root_folder.id,
            "custom_fields": {"criticality": "high"},
        }
        s = ProjectWriteSerializer(data=payload)
        assert s.is_valid(), s.errors
        instance = s.save()
        assert instance.custom_fields["criticality"] == "high"

    def test_write_updates_existing_custom_field(
        self, criticality_definition, root_folder
    ):
        p = Project.objects.create(name="P-update", folder=root_folder)
        p.set_custom_field("criticality", "low")
        payload = {"custom_fields": {"criticality": "high"}}
        s = ProjectWriteSerializer(instance=p, data=payload, partial=True)
        assert s.is_valid(), s.errors
        s.save()
        p.refresh_from_db()
        assert p.custom_fields["criticality"] == "high"

    def test_write_rejects_unknown_custom_field(self, root_folder):
        p = Project.objects.create(name="P-bad", folder=root_folder)
        payload = {"custom_fields": {"does_not_exist": "x"}}
        s = ProjectWriteSerializer(instance=p, data=payload, partial=True)
        assert s.is_valid(), s.errors
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            s.save()


# --- Regression tests for code-review findings ------------------------------


@pytest.mark.django_db
class TestReviewFixes:
    """One test per finding from the second-pass review."""

    # Fix #2: transaction wraps host create + custom_fields apply
    def test_serializer_create_rolls_back_host_on_custom_field_failure(
        self, criticality_definition, root_folder
    ):
        payload = {
            "name": "P-tx-rollback",
            "folder": root_folder.id,
            "custom_fields": {"criticality": "totally-bogus"},
        }
        s = ProjectWriteSerializer(data=payload)
        assert s.is_valid(), s.errors
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            s.save()
        # Host must NOT have been created — the whole save is wrapped in atomic.
        assert not Project.objects.filter(name="P-tx-rollback").exists()

    # Fix #3: multi_choice raises on unknown choice slug
    def test_multi_choice_raises_on_unknown_slug(self, project_ct, root_folder):
        d = FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="tags",
            label="Tags",
            type=FieldDefinition.Type.MULTI_CHOICE,
        )
        FieldChoice.objects.create(definition=d, value="alpha", label="Alpha")
        p = Project.objects.create(name="P-mc-bad", folder=root_folder)
        with pytest.raises(FieldChoice.DoesNotExist):
            p.set_custom_field("tags", ["alpha", "bogus"])

    # Fix #11: multi_choice [] clears the row, returning the default
    def test_multi_choice_empty_list_clears_row(self, project_ct, root_folder):
        d = FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="phases",
            label="Phases",
            type=FieldDefinition.Type.MULTI_CHOICE,
            default=["plan"],
        )
        FieldChoice.objects.create(definition=d, value="plan", label="Plan")
        FieldChoice.objects.create(definition=d, value="build", label="Build")
        p = Project.objects.create(name="P-mc-clear", folder=root_folder)
        p.set_custom_field("phases", ["build"])
        assert FieldValue.objects.filter(definition=d, object_id=p.id).exists()
        p.set_custom_field("phases", [])
        assert not FieldValue.objects.filter(definition=d, object_id=p.id).exists()
        # Reading falls back to the default.
        assert p.custom_fields["phases"] == ["plan"]

    # Fix #4: Actor.DoesNotExist surfaces as 400, not 500
    def test_serializer_unknown_actor_returns_400(self, project_ct, root_folder):
        FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="owner_actor",
            label="Owner",
            type=FieldDefinition.Type.ACTOR,
        )
        p = Project.objects.create(name="P-actor", folder=root_folder)
        payload = {
            "custom_fields": {"owner_actor": "00000000-0000-0000-0000-000000000000"}
        }
        s = ProjectWriteSerializer(instance=p, data=payload, partial=True)
        assert s.is_valid(), s.errors
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            s.save()
        # The error is per-field under custom_fields.
        detail = exc_info.value.detail
        assert "custom_fields" in detail
        assert "owner_actor" in detail["custom_fields"]

    # Fix #5: set_custom_field clears stale typed columns
    def test_set_custom_field_clears_stale_columns(self, project_ct, root_folder):
        d = FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="note",
            label="Note",
            type=FieldDefinition.Type.TEXT,
        )
        p = Project.objects.create(name="P-stale", folder=root_folder)
        p.set_custom_field("note", "hello")
        fv = FieldValue.objects.get(definition=d, object_id=p.id)
        assert fv.value_text == "hello"
        # Pretend the definition's type changed under the value.
        d.type = FieldDefinition.Type.NUMBER
        d.save()
        p.set_custom_field("note", 42)
        fv.refresh_from_db()
        assert fv.value_number == 42
        # Old column wiped:
        assert fv.value_text is None

    # Fix #6: cross-definition value_choice rejected at clean()
    def test_value_choice_must_belong_to_definition(self, project_ct, root_folder):
        d1 = FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="def1",
            label="Def 1",
            type=FieldDefinition.Type.SINGLE_CHOICE,
        )
        d2 = FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="def2",
            label="Def 2",
            type=FieldDefinition.Type.SINGLE_CHOICE,
        )
        choice_of_d2 = FieldChoice.objects.create(definition=d2, value="x", label="X")
        p = Project.objects.create(name="P-xref", folder=root_folder)
        from django.core.exceptions import ValidationError as DjangoValidationError

        with pytest.raises(DjangoValidationError):
            fv = FieldValue(
                definition=d1,
                content_type=project_ct,
                object_id=p.id,
                value_choice=choice_of_d2,
            )
            fv.full_clean()

    # Fix #7: deleting a referenced FieldDefinition → 409 Conflict
    def test_destroy_referenced_definition_raises_conflict(
        self, criticality_definition, root_folder
    ):
        from custom_fields.views import Conflict, FieldDefinitionViewSet

        p = Project.objects.create(name="P-ref", folder=root_folder)
        p.set_custom_field("criticality", "low")
        viewset = FieldDefinitionViewSet()
        with pytest.raises(Conflict):
            viewset.perform_destroy(criticality_definition)

    # Fix #8: deleting a referenced FieldChoice → 409 Conflict (via PROTECT)
    def test_destroy_referenced_choice_raises_conflict(
        self, criticality_definition, root_folder
    ):
        from custom_fields.views import Conflict, FieldChoiceViewSet

        p = Project.objects.create(name="P-choice-ref", folder=root_folder)
        p.set_custom_field("criticality", "high")
        high_choice = criticality_definition.choices.get(value="high")
        viewset = FieldChoiceViewSet()
        with pytest.raises(Conflict):
            viewset.perform_destroy(high_choice)

    # Fix #9: boolean garbage → no-op (None), not silent False filter
    def test_boolean_filter_garbage_returns_none_not_false_match(
        self, project_ct, root_folder
    ):
        from custom_fields.filters import _PARSE_FAILURE, _coerce

        assert _coerce("garbage", "boolean") is _PARSE_FAILURE
        assert _coerce("true", "boolean") is True
        assert _coerce("false", "boolean") is False

    # Fix #10: scalar garbage → empty queryset, not all rows
    def test_number_filter_garbage_returns_none_queryset(self, project_ct, root_folder):
        FieldDefinition.objects.create(
            target_content_type=project_ct,
            name="score",
            label="Score",
            type=FieldDefinition.Type.NUMBER,
        )
        Project.objects.create(name="P-num-1", folder=root_folder)
        Project.objects.create(name="P-num-2", folder=root_folder)
        fs = ProjectViewSet().filterset_class
        qs = fs(
            data={"field_score": "not-a-number"},
            queryset=Project.objects.filter(name__startswith="P-num-"),
        ).qs
        # Garbage in → empty result, NOT all rows.
        assert list(qs) == []

    # Fix #12: PATCH with explicit null clears all custom fields
    def test_patch_null_clears_all_custom_fields(
        self, criticality_definition, root_folder
    ):
        p = Project.objects.create(name="P-clear-all", folder=root_folder)
        p.set_custom_field("criticality", "high")
        assert p.custom_fields["criticality"] == "high"
        payload = {"custom_fields": None}
        s = ProjectWriteSerializer(instance=p, data=payload, partial=True)
        assert s.is_valid(), s.errors
        s.save()
        p.refresh_from_db()
        # Default is None (no `default` set on this definition).
        assert p.custom_fields.get("criticality") is None
        assert not FieldValue.objects.filter(object_id=p.id).exists()

    # Original review findings #14 and #15 (cache invalidation on re-target,
    # cache-key-includes-base) became no-ops once the process-level FilterSet
    # cache was removed — the FilterSet is rebuilt per request, so there is
    # nothing to invalidate. Test_new_definition_appears_immediately and
    # test_deleted_definition_disappears_immediately in TestFilterFreshness
    # cover the freshness contract directly.

    # Prefetch: list serialization should not N+1 on field_values.
    def test_prefetch_avoids_n_plus_one_on_list(
        self, criticality_definition, root_folder
    ):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        # Create several projects each with a value.
        projects = [
            Project.objects.create(name=f"P-list-{i}", folder=root_folder)
            for i in range(5)
        ]
        for p in projects:
            p.set_custom_field("criticality", "high")

        # Serialize via the prefetched queryset (mirrors what
        # CustomFieldsViewSetMixin.get_queryset does for list endpoints).
        qs = CustomFieldsMixin.prefetch_for_queryset(
            Project.objects.filter(name__startswith="P-list-")
        )
        with CaptureQueriesContext(connection) as ctx:
            data = [ProjectReadSerializer(p).data for p in qs]
        query_count_prefetched = len(ctx)

        # Same serialization WITHOUT prefetch — should fire more queries.
        qs_plain = Project.objects.filter(name__startswith="P-list-")
        with CaptureQueriesContext(connection) as ctx:
            _ = [ProjectReadSerializer(p).data for p in qs_plain]
        query_count_plain = len(ctx)

        assert all(d["custom_fields"]["criticality"] == "high" for d in data)
        # Prefetched path issues strictly fewer queries than the naive one.
        assert query_count_prefetched < query_count_plain, (
            f"prefetch did nothing: {query_count_prefetched} vs {query_count_plain}"
        )

    # N+1 sanity: the property is cached on the instance, so consecutive
    # accesses share a single computation.
    def test_custom_fields_property_caches_on_instance(
        self, criticality_definition, root_folder
    ):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        p = Project.objects.create(name="P-cache", folder=root_folder)
        p.set_custom_field("criticality", "low")
        # First access fires queries.
        with CaptureQueriesContext(connection) as ctx:
            _ = p.custom_fields
        first_count = len(ctx)
        # Second access is free.
        with CaptureQueriesContext(connection) as ctx:
            _ = p.custom_fields
        assert len(ctx) == 0, (
            f"expected cached access, got {len(ctx)} queries; first was {first_count}"
        )

    # validate_name (per the Phase-2 plausible finding C6): Unicode rejected
    def test_definition_name_rejects_unicode(self):
        from custom_fields.serializers import FieldDefinitionWriteSerializer
        from rest_framework import serializers as drf

        s = FieldDefinitionWriteSerializer()
        with pytest.raises(drf.ValidationError):
            s.validate_name("Café")
        with pytest.raises(drf.ValidationError):
            s.validate_name("has spaces")
        # ASCII slugs lowercased
        assert s.validate_name("Criticality_V2") == "criticality_v2"
