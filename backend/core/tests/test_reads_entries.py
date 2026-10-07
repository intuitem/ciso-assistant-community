"""Integrity of the readable-models registry. Every entry is a contract
between a consumer and the database; these tests hold each one to the rules
in ReadEntry's docstring so a new entry cannot quietly break them."""

import dataclasses

import pytest
from django.contrib.auth.models import Permission
from django.db.models import IntegerField, Q
from django.db.models.fields.related import ForeignObjectRel

from core.reads import BASE_READ_FIELDS, READABLE_MODELS, ReadEntry, get_model_field

ENTRIES = sorted(READABLE_MODELS.items())


def follow(model, path):
    """The field at the end of a ``__`` path, or None when a segment does
    not exist. Reverse relations count: prefetches walk them."""
    field = None
    for segment in path.split("__"):
        try:
            field = model._meta.get_field(segment)
        except Exception:  # noqa: BLE001 - FieldDoesNotExist and friends
            return None
        model = field.related_model
        if model is None:
            return None
    return field


@pytest.mark.parametrize("key, entry", ENTRIES)
class TestEveryEntry:
    def test_keys_are_snake_case_model_names(self, key, entry):
        assert key == key.lower() and " " not in key

    def test_fields_are_concrete_columns_of_the_model(self, key, entry):
        for name in entry.fields:
            assert "__" not in name, f"{key}.{name} tunnels into another object"
            assert get_model_field(entry.model, name) is not None, f"{key}.{name}"

    def test_readable_fields_keep_the_base_columns_the_model_has(self, key, entry):
        readable = entry.readable_fields()
        columns = {f.name for f in entry.model._meta.concrete_fields}
        for base in BASE_READ_FIELDS:
            assert (base in readable) == (base in columns), f"{key}.{base}"
        assert readable[len(readable) - len(entry.fields) :] == entry.fields
        assert len(readable) == len(set(readable)), f"{key} lists a column twice"

    def test_the_model_is_folder_scoped(self, key, entry):
        assert get_model_field(entry.model, "folder") is not None, key

    def test_optional_values_do_not_shadow_always_on_ones(self, key, entry):
        assert not set(entry.optional_computed) & set(entry.computed), key

    def test_computed_values_are_callables(self, key, entry):
        for name, resolve in {**entry.computed, **entry.optional_computed}.items():
            assert callable(resolve), f"{key}.{name}"

    def test_relation_paths_resolve(self, key, entry):
        for path in entry.select_related:
            field = follow(entry.model, path)
            assert field is not None and not isinstance(field, ForeignObjectRel), (
                f"{key}: select_related {path!r}"
            )
        for path in entry.prefetch_related:
            assert follow(entry.model, path) is not None, f"{key}: prefetch {path!r}"

    def test_scoped_prefetch_paths_resolve_to_the_declared_model(self, key, entry):
        for name, group in entry.prefetch_scoped.items():
            assert name in entry.computed or name in entry.optional_computed, (
                f"{key}: prefetch_scoped {name!r} is keyed by no computed value"
            )
            for path, model in group.items():
                field = follow(entry.model, path)
                assert field is not None, f"{key}: prefetch_scoped {path!r}"
                assert field.related_model is model, f"{key}: {path!r} is not {model}"
                parent = path.rpartition("__")[0]
                assert not parent or parent in group, (
                    f"{key}: {path!r} nests under an undeclared parent"
                )

    def test_unrated_sentinels_are_integer_columns(self, key, entry):
        for name in entry.skip_unrated:
            field = get_model_field(entry.model, name)
            assert isinstance(field, IntegerField), f"{key}.{name}"
            assert name in entry.fields, f"{key}.{name} is guarded but not readable"

    def test_base_filter_is_a_q_or_absent(self, key, entry):
        assert entry.base_filter is None or isinstance(entry.base_filter, Q)


@pytest.mark.django_db
class TestEveryEntryWithDatabase:
    @pytest.mark.parametrize("key, entry", ENTRIES)
    def test_the_model_has_a_view_permission(self, key, entry):
        codename = f"view_{entry.model._meta.model_name}"
        assert Permission.objects.filter(codename=codename).exists(), codename


class TestReadEntry:
    def test_is_frozen(self):
        entry = READABLE_MODELS["applied_control"]
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.fields = []

    def test_models_are_distinct_across_entries(self):
        models = [entry.model for _key, entry in ENTRIES]
        assert len(models) == len(set(models))

    def test_nameless_models_drop_name_from_the_base_columns(self):
        for key in ("requirement_assessment", "validation_flow", "task_node"):
            readable = READABLE_MODELS[key].readable_fields()
            assert "name" not in readable, key
            assert {"id", "created_at", "updated_at"} <= set(readable), key

    def test_a_fresh_entry_defaults_to_nothing_extra(self):
        from core.models import AppliedControl

        entry = ReadEntry(model=AppliedControl, fields=["status"])
        assert entry.computed == {} and entry.optional_computed == {}
        assert entry.prefetch_scoped == {} and entry.base_filter is None
        assert entry.skip_unrated == frozenset()
        assert entry.select_related == [] and entry.prefetch_related == []
        assert entry.readable_fields() == [*BASE_READ_FIELDS, "status"]
