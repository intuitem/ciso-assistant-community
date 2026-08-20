import pytest

from iam.models import Folder
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.serializers import (
    CustomMetricSampleWriteSerializer,
    MetricDefinitionWriteSerializer,
    MetricInstanceReadSerializer,
)


_UNSET = object()


def _errors_for_choices_definition(choices_definition=_UNSET):
    data = {}
    if choices_definition is not _UNSET:
        data["choices_definition"] = choices_definition

    serializer = MetricDefinitionWriteSerializer(data=data)
    serializer.is_valid()
    return serializer.errors


def test_choices_definition_with_ref_ids_has_no_field_error():
    errors = _errors_for_choices_definition(
        [
            {"ref_id": "low", "name": "Low"},
            {"ref_id": "high", "name": "High"},
        ]
    )

    assert "choices_definition" not in errors


def test_choices_definition_rejects_empty_ref_id():
    errors = _errors_for_choices_definition([{"ref_id": "", "name": "Low"}])

    assert "choices_definition" in errors


def test_choices_definition_rejects_missing_ref_id():
    errors = _errors_for_choices_definition([{"name": "Low"}])

    assert "choices_definition" in errors


def test_choices_definition_none_or_absent_has_no_field_error():
    assert "choices_definition" not in _errors_for_choices_definition(None)
    assert "choices_definition" not in _errors_for_choices_definition()


def test_choices_definition_rejects_whitespace_ref_id():
    errors = _errors_for_choices_definition([{"ref_id": "   ", "name": "Low"}])

    assert "choices_definition" in errors


@pytest.fixture
def root():
    return Folder.get_root_folder()


@pytest.fixture
def quantitative_definition(root):
    return MetricDefinition.objects.create(
        name="Uptime", category=MetricDefinition.Category.QUANTITATIVE
    )


@pytest.fixture
def metric_instance(root, quantitative_definition):
    return MetricInstance.objects.create(
        name="ALM Uptime", folder=root, metric_definition=quantitative_definition
    )


def _sample_with_value(metric_instance, value):
    from django.utils import timezone

    return CustomMetricSample.objects.create(
        metric_instance=metric_instance,
        folder=metric_instance.folder,
        timestamp=timezone.now(),
        value=value,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("bad_value", [1.0, "99.9", [1.0], True])
class TestMalformedSampleValueDoesNotCrash:
    def test_raw_value_does_not_raise(self, metric_instance, bad_value):
        _sample_with_value(metric_instance, bad_value)

        assert metric_instance.raw_value() is None

    def test_display_value_does_not_raise(self, metric_instance, bad_value):
        _sample_with_value(metric_instance, bad_value)

        assert metric_instance.current_value() == "N/A"

    def test_read_serializer_does_not_raise(self, metric_instance, bad_value):
        _sample_with_value(metric_instance, bad_value)

        data = MetricInstanceReadSerializer(metric_instance).data

        assert data["current_value"] == "N/A"
        assert data["raw_value"] is None


@pytest.mark.django_db
def test_well_formed_quantitative_value_still_works(metric_instance):
    _sample_with_value(metric_instance, {"result": 42.0})

    assert metric_instance.raw_value() == 42.0
    assert metric_instance.current_value() == "42.0"


@pytest.mark.django_db
class TestCustomMetricSampleWriteSerializerValidatesValueShape:
    def _errors_for_value(self, metric_instance, value):
        serializer = CustomMetricSampleWriteSerializer(
            data={
                "metric_instance": str(metric_instance.pk),
                "timestamp": "2024-01-01T00:00:00Z",
                "value": value,
            }
        )
        serializer.is_valid()
        return serializer.errors

    @pytest.mark.parametrize("bad_value", [1.0, "99.9", [1.0], True])
    def test_rejects_non_object_value(self, metric_instance, bad_value):
        errors = self._errors_for_value(metric_instance, bad_value)

        assert "value" in errors

    def test_accepts_result_object(self, metric_instance):
        errors = self._errors_for_value(metric_instance, {"result": 1.0})

        assert "value" not in errors

    def test_accepts_choice_index_object(self, metric_instance):
        errors = self._errors_for_value(metric_instance, {"choice_index": 1})

        assert "value" not in errors
