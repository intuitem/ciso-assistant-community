"""Registry of local models that can be synced with remote ITSM systems.

Single source of truth for: which local models are syncable, their mappable
fields and field types, choice values for the UI, and content_type <-> model_key
resolution. Adding a new syncable model is a matter of registering a
``SyncableModelSpec`` here and opting the model into ``IntegrationSyncableMixin``.

Specs are declared as literals (no ``core.models`` import) to keep this module
import-light and cycle-free; a test pins field-key parity against the models.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from django.contrib.contenttypes.models import ContentType

# Field types understood by the mapper/frontend.
STRING = "string"
TEXT = "text"
DATE = "date"
CHOICE = "choice"


@dataclass(frozen=True)
class FieldSpec:
    key: str  # local model field name
    type: str  # STRING | TEXT | DATE | CHOICE
    required: bool = False
    # (value, label) pairs for CHOICE fields. Labels are i18n message keys the
    # frontend resolves with safeTranslate; the backend only needs the values.
    choices: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SyncableModelSpec:
    key: str  # stable key, e.g. "applied_control", "asset"
    app_label: str  # e.g. "core"
    model_name: str  # Django ContentType model name (lowercased)
    label: str  # i18n message key for the UI
    fields: tuple[FieldSpec, ...] = dataclass_field(default_factory=tuple)


# NOTE: ``fields`` lists the MAPPABLE / UI-shown fields (what FieldMapper renders
# and the mappers may map), which is intentionally distinct from a model's
# INTEGRATION_SYNCABLE_FIELDS (the broader change-detection set used to decide
# whether a save triggers a sync).

_APPLIED_CONTROL = SyncableModelSpec(
    key="applied_control",
    app_label="core",
    model_name="appliedcontrol",
    label="appliedControls",
    fields=(
        FieldSpec("name", STRING, required=True),
        FieldSpec("description", TEXT),
        FieldSpec("eta", DATE),
        FieldSpec("ref_id", STRING),
        FieldSpec(
            "status",
            CHOICE,
            choices=(
                ("to_do", "toDo"),
                ("in_progress", "inProgress"),
                ("on_hold", "onHold"),
                ("active", "active"),
                ("degraded", "degraded"),
                ("deprecated", "deprecated"),
            ),
        ),
        FieldSpec(
            "priority",
            CHOICE,
            choices=(("1", "p1"), ("2", "p2"), ("3", "p3"), ("4", "p4")),
        ),
    ),
)

_ASSET = SyncableModelSpec(
    key="asset",
    app_label="core",
    model_name="asset",
    label="assets",
    fields=(
        FieldSpec("name", STRING, required=True),
        FieldSpec("description", TEXT),
        FieldSpec("ref_id", STRING),
        FieldSpec("type", CHOICE, choices=(("PR", "primary"), ("SP", "support"))),
        FieldSpec("reference_link", STRING),
        FieldSpec("observation", TEXT),
    ),
)

SYNCABLE_MODELS: dict[str, SyncableModelSpec] = {
    _APPLIED_CONTROL.key: _APPLIED_CONTROL,
    _ASSET.key: _ASSET,
}


def get_spec(model_key: str) -> SyncableModelSpec | None:
    return SYNCABLE_MODELS.get(model_key)


def all_specs() -> list[SyncableModelSpec]:
    return list(SYNCABLE_MODELS.values())


def model_key_for_content_type(content_type: ContentType) -> str | None:
    for spec in SYNCABLE_MODELS.values():
        if (
            spec.app_label == content_type.app_label
            and spec.model_name == content_type.model
        ):
            return spec.key
    return None


def content_type_for_model_key(model_key: str) -> ContentType | None:
    spec = get_spec(model_key)
    if not spec:
        return None
    return ContentType.objects.get_by_natural_key(spec.app_label, spec.model_name)


def choice_fields(model_key: str) -> set[str]:
    spec = get_spec(model_key)
    if not spec:
        return set()
    return {f.key for f in spec.fields if f.type == CHOICE}


def date_fields(model_key: str) -> set[str]:
    spec = get_spec(model_key)
    if not spec:
        return set()
    return {f.key for f in spec.fields if f.type == DATE}


def mappable_field_keys(model_key: str) -> set[str]:
    spec = get_spec(model_key)
    if not spec:
        return set()
    return {f.key for f in spec.fields}
