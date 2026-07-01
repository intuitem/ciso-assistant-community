from metrology.serializers import MetricDefinitionWriteSerializer


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
