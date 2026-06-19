from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.dateparse import parse_date
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from iam.models import Folder, FolderMixin, PublishInRootFolderMixin


class FieldType(models.TextChoices):
    TEXT = "text", _("Text")
    NUMBER = "number", _("Number")
    DATE = "date", _("Date")
    BOOLEAN = "boolean", _("Boolean")
    CHOICE = "choice", _("Choice")
    MULTI_CHOICE = "multi_choice", _("Multiple choice")


# Each field type is stored in exactly one typed column of CustomFieldValue.
TYPE_TO_COLUMN = {
    FieldType.TEXT: "value_text",
    FieldType.NUMBER: "value_number",
    FieldType.DATE: "value_date",
    FieldType.BOOLEAN: "value_boolean",
    FieldType.CHOICE: "value_text",
    FieldType.MULTI_CHOICE: "value_text",
}

# Only value_text-backed types can be searched (search scans value_text).
SEARCHABLE_TYPES = frozenset(
    t for t, col in TYPE_TO_COLUMN.items() if col == "value_text"
)


def coerce_value(field_type: str, raw):
    """Coerce a raw input to the python value stored in the typed column.

    Returns the value to assign to the column named by TYPE_TO_COLUMN[field_type].
    For choice/multi_choice this is the choice *value* slug (a string); the caller
    is responsible for validating it against the definition's choices.
    Raises ``ValueError`` on bad input.
    """
    if raw is None or raw == "":
        return None

    if field_type == FieldType.NUMBER:
        try:
            return Decimal(str(raw))
        except InvalidOperation, ValueError, TypeError:
            raise ValueError(f"'{raw}' is not a valid number")

    if field_type == FieldType.DATE:
        if isinstance(raw, datetime):
            return raw.date()
        if isinstance(raw, date):
            return raw
        parsed = parse_date(str(raw))
        if parsed is None:
            raise ValueError(f"'{raw}' is not a valid ISO date (YYYY-MM-DD)")
        return parsed

    if field_type == FieldType.BOOLEAN:
        if isinstance(raw, bool):
            return raw
        token = str(raw).strip().lower()
        if token in ("true", "1"):
            return True
        if token in ("false", "0"):
            return False
        raise ValueError(f"'{raw}' is not a valid boolean")

    # text, choice, multi_choice → stored as text
    return str(raw)


class CustomFieldDefinition(FolderMixin, PublishInRootFolderMixin, AbstractBaseModel):
    """Schema of an org-defined field attached to a host model.

    Scoping (design B): the inherited ``folder`` decides where the field applies.
    A definition in the root folder is global; one in a domain applies to that
    domain's subtree only. See :meth:`for_object`.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="custom_field_definitions",
        verbose_name=_("model"),
    )
    key = models.SlugField(max_length=64, verbose_name=_("key"))
    label = models.CharField(max_length=200, verbose_name=_("label"))
    help_text = models.TextField(blank=True, default="", verbose_name=_("help text"))
    translations = models.JSONField(
        null=True, blank=True, verbose_name=_("translations")
    )
    field_type = models.CharField(
        max_length=20, choices=FieldType.choices, verbose_name=_("field type")
    )
    required = models.BooleanField(default=False, verbose_name=_("required"))
    visible = models.BooleanField(default=True, verbose_name=_("visible"))
    searchable = models.BooleanField(default=False, verbose_name=_("searchable"))
    filterable = models.BooleanField(default=True, verbose_name=_("filterable"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("order"))

    class Meta:
        verbose_name = _("custom field definition")
        verbose_name_plural = _("custom field definitions")
        ordering = ["order", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "folder", "key"],
                name="unique_custom_field_key_per_model_folder",
            )
        ]

    def __str__(self):
        return f"{self.label} ({self.content_type.model}.{self.key})"

    @property
    def value_column(self) -> str:
        return TYPE_TO_COLUMN[self.field_type]

    @property
    def is_choice(self) -> bool:
        return self.field_type in (FieldType.CHOICE, FieldType.MULTI_CHOICE)

    @property
    def label_localized(self) -> str:
        return (
            (self.translations or {}).get(get_language(), {}).get("label", self.label)
        )

    @property
    def help_text_localized(self) -> str:
        return (
            (self.translations or {})
            .get(get_language(), {})
            .get("help_text", self.help_text)
        )

    def clean(self):
        super().clean()
        # Guard against ambiguity: an object resolves a single field set, so a key
        # must be unique along any root↔leaf chain it could belong to. Reject a key
        # that collides with an ancestor-or-descendant definition of the same model.
        siblings = CustomFieldDefinition.objects.filter(
            content_type_id=self.content_type_id, key=self.key
        ).exclude(pk=self.pk)
        if not siblings.exists():
            return
        # A key must resolve to a single type (hence a single value column) across
        # ALL folders, so list filtering/search by `cf__<key>` is unambiguous even
        # for a queryset spanning sibling folders. Enforced here (model level) so it
        # holds for every write path, not just the API serializer.
        if siblings.exclude(field_type=self.field_type).exists():
            raise ValidationError(
                {
                    "field_type": _(
                        "A custom field with this key already exists for this model "
                        "with a different type."
                    )
                }
            )
        my_chain = self._ancestor_or_self_ids(self.folder)
        for other in siblings.select_related("folder"):
            other_chain = self._ancestor_or_self_ids(other.folder)
            if other.folder_id in my_chain or self.folder_id in other_chain:
                raise ValidationError(
                    {
                        "key": _(
                            "A custom field with this key already exists for this model "
                            "in an overlapping folder scope."
                        )
                    }
                )

    @staticmethod
    def _ancestor_or_self_ids(folder: Folder) -> set:
        ids = {folder.id}
        ids.update(f.id for f in folder.get_parent_folders())
        return ids

    @classmethod
    def for_object(cls, obj) -> models.QuerySet["CustomFieldDefinition"]:
        """Definitions that apply to ``obj``: global ones plus those owned by an
        ancestor-or-self folder of the object's folder."""
        ct = ContentType.objects.get_for_model(obj.__class__)
        folder_ids = {Folder.get_root_folder_id()}
        obj_folder = getattr(obj, "folder", None)
        if obj_folder is not None:
            folder_ids |= cls._ancestor_or_self_ids(obj_folder)
        return cls.objects.filter(content_type=ct, folder_id__in=folder_ids)


class CustomFieldChoice(AbstractBaseModel):
    """An allowed value for a choice / multi_choice definition."""

    definition = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name=_("definition"),
    )
    value = models.SlugField(max_length=64, verbose_name=_("value"))
    label = models.CharField(max_length=200, verbose_name=_("label"))
    translations = models.JSONField(
        null=True, blank=True, verbose_name=_("translations")
    )
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("order"))

    @property
    def label_localized(self) -> str:
        return (
            (self.translations or {}).get(get_language(), {}).get("label", self.label)
        )

    class Meta:
        verbose_name = _("custom field choice")
        verbose_name_plural = _("custom field choices")
        ordering = ["order", "value"]
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "value"],
                name="unique_custom_field_choice_value",
            )
        ]

    def __str__(self):
        return self.label


class CustomFieldValue(AbstractBaseModel):
    """A single typed value of a definition for one host object.

    Exactly one ``value_*`` column is populated, selected by the definition's type.
    multi_choice fields keep one row per selected choice.
    """

    definition = models.ForeignKey(
        CustomFieldDefinition,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name=_("definition"),
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+"
    )
    object_id = models.UUIDField()
    host = GenericForeignKey("content_type", "object_id")

    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    value_date = models.DateField(null=True, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = _("custom field value")
        verbose_name_plural = _("custom field values")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["definition", "value_text"]),
            models.Index(fields=["definition", "value_number"]),
            models.Index(fields=["definition", "value_date"]),
            models.Index(fields=["definition", "value_boolean"]),
        ]
        # Single-value uniqueness (one row per definition+object) is enforced in the
        # write layer (see set_custom_fields). A DB constraint can't express it: a
        # partial condition cannot span the relation to definition.field_type, and
        # multi_choice deliberately keeps several rows per object.
        # DEFERRED: a DB-backed guarantee (denormalize is_multi + partial unique)
        # to close the concurrent-write race — see project-custom-fields memory.

    def __str__(self):
        return f"{self.definition.key}={self.value}"

    @property
    def value(self):
        return getattr(self, self.definition.value_column)
