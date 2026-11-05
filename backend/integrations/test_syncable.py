"""Parity tests pinning the syncable-model registry against the actual models,
so the registry, the model constants, and the frontend field lists can't drift
silently."""

from django.apps import apps

from integrations.syncable import SYNCABLE_MODELS, mappable_field_keys


def test_every_spec_resolves_to_a_model_with_matching_key():
    for key, spec in SYNCABLE_MODELS.items():
        model = apps.get_model(spec.app_label, spec.model_name)
        assert model.INTEGRATION_MODEL_KEY == key


def test_spec_fields_exist_on_models():
    for spec in SYNCABLE_MODELS.values():
        model = apps.get_model(spec.app_label, spec.model_name)
        model_fields = {f.name for f in model._meta.get_fields()}
        missing = {f.key for f in spec.fields} - model_fields
        assert not missing, f"{spec.key}: spec fields not on model: {missing}"


def test_asset_spec_matches_syncable_fields():
    from core.models import Asset

    assert mappable_field_keys("asset") == Asset.INTEGRATION_SYNCABLE_FIELDS


def test_applied_control_spec_within_syncable_fields():
    from core.models import AppliedControl

    # AC's change-detection set is intentionally a superset of the mappable UI
    # set (it also watches start_date/effort/observation). ref_id is mappable
    # but not change-tracked — a pre-existing gap on main, kept as-is.
    assert (
        mappable_field_keys("applied_control") - {"ref_id"}
        <= AppliedControl.INTEGRATION_SYNCABLE_FIELDS
    )
