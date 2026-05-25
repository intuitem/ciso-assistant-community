"""Custom fields — org-defined typed fields any opted-in model can carry."""

from auditlog.registry import auditlog
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel


class FieldDefinition(AbstractBaseModel):
    class Type(models.TextChoices):
        TEXT = "text", _("Text")
        LONG_TEXT = "long_text", _("Long text")
        URL = "url", _("URL")
        NUMBER = "number", _("Number")
        BOOLEAN = "boolean", _("Boolean")
        DATE = "date", _("Date")
        DATETIME = "datetime", _("Date and time")
        SINGLE_CHOICE = "single_choice", _("Single choice")
        MULTI_CHOICE = "multi_choice", _("Multi choice")
        ACTOR = "actor", _("Actor")

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name=_("Target model"),
    )
    name = models.CharField(
        max_length=64,
        verbose_name=_("Internal name"),
        help_text=_("Lowercase ASCII slug. Used as ?field_<name>= in API filters."),
    )
    label = models.CharField(max_length=200, verbose_name=_("Label"))
    description = models.TextField(blank=True, default="")
    translations = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Per-locale label overrides, e.g. {"fr": "Criticité"}.'),
    )
    type = models.CharField(max_length=32, choices=Type.choices, default=Type.TEXT)
    required = models.BooleanField(default=False)
    default = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Default value when no FieldValue exists. Must match `type`."),
    )
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    filterable = models.BooleanField(default=True)
    builtin = models.BooleanField(
        default=False,
        help_text=_("Seeded by migration/library. Protected from UI deletion."),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["target_content_type", "name"],
                name="uniq_field_def_per_ct_name",
            )
        ]
        ordering = ["target_content_type", "order", "name"]
        verbose_name = _("Field definition")
        verbose_name_plural = _("Field definitions")

    def __str__(self) -> str:
        return f"{self.target_content_type.model}.{self.name}"


class FieldChoice(AbstractBaseModel):
    definition = models.ForeignKey(
        FieldDefinition,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    value = models.CharField(max_length=64)
    label = models.CharField(max_length=200)
    translations = models.JSONField(default=dict, blank=True)
    color = models.CharField(max_length=32, blank=True, default="")
    order = models.PositiveSmallIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "value"],
                name="uniq_field_choice_per_def_value",
            )
        ]
        ordering = ["definition", "order", "value"]
        verbose_name = _("Field choice")
        verbose_name_plural = _("Field choices")

    def __str__(self) -> str:
        return f"{self.definition.name}={self.value}"


class FieldValue(AbstractBaseModel):
    """One custom-field value attached to a host record via a GenericForeignKey.
    Read through `resolved_value`; raw value_* columns bypass type dispatch."""

    definition = models.ForeignKey(
        FieldDefinition,
        on_delete=models.PROTECT,
        related_name="values",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="+",
    )
    object_id = models.UUIDField()
    host = GenericForeignKey("content_type", "object_id")

    value_text = models.TextField(null=True, blank=True)
    value_number = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    value_boolean = models.BooleanField(null=True, blank=True)
    value_date = models.DateField(null=True, blank=True)
    value_datetime = models.DateTimeField(null=True, blank=True)
    # PROTECT not SET_NULL: prevent silent loss of historical values.
    value_choice = models.ForeignKey(
        FieldChoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    value_choices = models.ManyToManyField(
        FieldChoice,
        blank=True,
        related_name="multi_values",
    )
    value_actor = models.ForeignKey(
        "core.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "content_type", "object_id"],
                name="uniq_field_value_per_def_host",
            )
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        verbose_name = _("Field value")
        verbose_name_plural = _("Field values")

    def __str__(self) -> str:
        return f"{self.definition.name}={self.resolved_value}"

    def clean(self) -> None:
        # Raw ORM can attach a value_choice from a different definition,
        # bypassing set_custom_field's scoped lookup. Block at clean().
        if self.value_choice_id and self.definition_id:
            if self.value_choice.definition_id != self.definition_id:
                raise ValidationError(
                    {"value_choice": "Choice does not belong to this field definition."}
                )
        super().clean()

    @property
    def resolved_value(self):
        d_type = self.definition.type
        if d_type in ("text", "long_text", "url"):
            return self.value_text
        if d_type == "number":
            return self.value_number
        if d_type == "boolean":
            return self.value_boolean
        if d_type == "date":
            return self.value_date
        if d_type == "datetime":
            return self.value_datetime
        if d_type == "single_choice":
            return self.value_choice.value if self.value_choice else None
        if d_type == "multi_choice":
            return [c.value for c in self.value_choices.all()]
        if d_type == "actor":
            return str(self.value_actor_id) if self.value_actor_id else None
        return None


_common_exclude = ["created_at", "updated_at"]
auditlog.register(FieldDefinition, exclude_fields=_common_exclude)
auditlog.register(FieldChoice, exclude_fields=_common_exclude)
auditlog.register(
    FieldValue,
    m2m_fields={"value_choices"},
    exclude_fields=_common_exclude,
)
