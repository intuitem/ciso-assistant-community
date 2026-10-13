"""Structural checks on SEARCHABLE_MODELS.

The entries build ORM filters, so a wrong field name surfaces as a FieldError on a user's
search, not at import — and a forgotten `ref_id=True` is silent.
"""

import pytest

from core.search import SEARCHABLE_MODELS


def _field_names(model):
    return {f.name for f in model._meta.get_fields()}


def _ids(entries):
    return [entry["slug"] for entry in entries]


@pytest.mark.parametrize("entry", SEARCHABLE_MODELS, ids=_ids(SEARCHABLE_MODELS))
def test_searchable_model_has_the_base_fields(entry):
    """Both are searched unconditionally."""
    fields = _field_names(entry["model"])
    assert "name" in fields, f"{entry['model'].__name__} has no `name` field"
    assert "description" in fields, (
        f"{entry['model'].__name__} has no `description` field"
    )


@pytest.mark.parametrize("entry", SEARCHABLE_MODELS, ids=_ids(SEARCHABLE_MODELS))
def test_ref_id_flag_matches_the_model(entry):
    """Opt-in and silent: a model with a ref_id but no flag is unfindable by reference."""
    has_field = "ref_id" in _field_names(entry["model"])
    assert entry["ref_id"] == has_field, (
        f"{entry['model'].__name__}: ref_id={entry['ref_id']} but the model "
        f"{'has' if has_field else 'has no'} a ref_id field"
    )


@pytest.mark.parametrize("entry", SEARCHABLE_MODELS, ids=_ids(SEARCHABLE_MODELS))
def test_extra_search_paths_resolve(entry):
    """A bad path is a runtime FieldError."""
    for path in entry["extra_search"]:
        model = entry["model"]
        for part in path.split("__"):
            field = model._meta.get_field(part)  # raises FieldDoesNotExist if wrong
            if field.related_model:
                model = field.related_model


def test_slugs_are_unique():
    slugs = _ids(SEARCHABLE_MODELS)
    assert len(slugs) == len(set(slugs)), "duplicate slug in SEARCHABLE_MODELS"
